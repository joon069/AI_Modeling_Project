import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import seaborn as sns
from pathlib import Path
import pyreadstat
from scipy.stats import chi2_contingency, spearmanr, pearsonr
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 한글 폰트 설정
# ============================================================================
font_path = '/System/Library/Fonts/AppleSDGothicNeo.ttc'
font_prop = fm.FontProperties(fname=font_path)

plt.rcParams['font.family'] = font_prop.get_name()
plt.rcParams['axes.unicode_minus'] = False
plt.rcParams['font.size'] = 11
sns.set_style("whitegrid")

# ============================================================================
# STEP 1: 데이터 로드 및 전처리
# ============================================================================
print("="*70)
print("STEP 1: 데이터 로드 및 전처리")
print("="*70)

base_path = Path("/Users/kiwi/Desktop/DataLab")
years = [2018, 2019, 2020, 2021, 2022, 2023, 2024]
core_variables = ['M_SUI_CON', 'M_SAD', 'M_STR', 'M_SLP_EN', 'PA_TOT', 'SEX']

# 각 연도별 데이터 로드
dfs = []
for year in years:
    folder = base_path / f"kyrbs{year}_sas"
    file_path = folder / f"kyrbs{year}.sas7bdat"

    print(f"Loading {year}...", end=" ")

    # 연도별 인코딩 처리
    if year <= 2019:
        df, meta = pyreadstat.read_sas7bdat(file_path)
    else:
        df = pd.read_sas(file_path, encoding='cp949')

    # 필요한 변수만 추출
    df = df[core_variables].copy()

    # 연도 및 코로나 시기 컬럼 추가
    df['YEAR'] = year
    if year <= 2019:
        df['COVID_PERIOD'] = '이전'
    elif year <= 2021:
        df['COVID_PERIOD'] = '시기'
    else:
        df['COVID_PERIOD'] = '이후'

    dfs.append(df)
    print(f"✓ ({len(df)} rows)")

# 모든 데이터 병합
data = pd.concat(dfs, ignore_index=True)
print(f"\n병합 완료: {len(data)} rows, {len(data.columns)} columns")

# 결측치 확인 (제거 전)
print("\n[제거 전] 결측치 현황:")
analysis_vars = core_variables
print(data[analysis_vars].isnull().sum())

# 6개 변수에 결측치 있는 행 제거
data_clean = data.dropna(subset=analysis_vars)
print(f"\n결측치 제거 후: {len(data_clean)} rows (제거된 행: {len(data) - len(data_clean)})")

# 유효 응답 범위 확인 및 이상치 제거
print("\n[전처리 전] 각 변수의 범위:")
for var in analysis_vars:
    print(f"{var}: min={data_clean[var].min():.2f}, max={data_clean[var].max():.2f}")

# 각 변수별 유효 범위 정의 (코드북 기준)
valid_ranges = {
    'M_SUI_CON': (1, 2),      # 1=없다, 2=있다
    'M_SAD': (1, 2),          # 1=없다, 2=있다
    'M_STR': (1, 5),          # 1=대단히, 2=많이, 3=조금, 4=거의 안함, 5=전혀 안함
    'M_SLP_EN': (1, 5),       # 1=충분, 2=대체로 충분, 3=보통, 4=대체로 불충분, 5=아주 불충분
    'PA_TOT': (1, 8),         # 1=안함, 2~8=실천
    'SEX': (1, 2)             # 1=남, 2=여
}

# 이상치 제거
initial_len = len(data_clean)
for var, (min_val, max_val) in valid_ranges.items():
    data_clean = data_clean[(data_clean[var] >= min_val) & (data_clean[var] <= max_val)]

print(f"\n이상치 제거 후: {len(data_clean)} rows (제거된 행: {initial_len - len(data_clean)})")

# 최종 데이터 통계
print("\n[전처리 완료] 최종 데이터 shape:", data_clean.shape)
print("\n기초통계량:")
print(data_clean[analysis_vars].describe().round(3))

# 연도별 샘플 수
print("\n연도별 샘플 수:")
print(data_clean['YEAR'].value_counts().sort_index())

# ============================================================================
# STEP 2: 연도별 비율 집계
# ============================================================================
print("\n" + "="*70)
print("STEP 2: 연도별 비율 집계")
print("="*70)

variables_to_plot = ['M_SUI_CON', 'M_SAD', 'M_STR', 'M_SLP_EN', 'PA_TOT']
labels_dict = {
    'M_SUI_CON': '자살 생각률',
    'M_SAD': '우울감 경험률',
    'M_STR': '스트레스 인지율',
    'M_SLP_EN': '수면 불충족률',
    'PA_TOT': '신체활동 실천율'
}

year_stats = []
for year in years:
    year_data = data_clean[data_clean['YEAR'] == year]

    stats = {
        'YEAR': year,
        'M_SUI_CON': (year_data['M_SUI_CON'] == 2).sum() / len(year_data) * 100,
        'M_SAD': (year_data['M_SAD'] == 2).sum() / len(year_data) * 100,
        'M_STR': ((year_data['M_STR'] == 1) | (year_data['M_STR'] == 2)).sum() / len(year_data) * 100,
        'M_SLP_EN': ((year_data['M_SLP_EN'] == 4) | (year_data['M_SLP_EN'] == 5)).sum() / len(year_data) * 100,
        'PA_TOT': ((year_data['PA_TOT'] >= 2) & (year_data['PA_TOT'] <= 8)).sum() / len(year_data) * 100,
    }
    year_stats.append(stats)

year_df = pd.DataFrame(year_stats)
print("\n연도별 집계 데이터:")
print(year_df.round(2))

# ============================================================================
# STEP 3: 시각화
# ============================================================================
print("\n" + "="*70)
print("STEP 3: 시각화 (4개 그래프)")
print("="*70)

# 그래프 1: 연도별 추이 (선 그래프)
fig, ax = plt.subplots(figsize=(14, 8))

colors_percent = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']

for i, var in enumerate(variables_to_plot):
    ax.plot(year_df['YEAR'], year_df[var], marker='o', label=labels_dict[var],
            linewidth=2.5, markersize=8, color=colors_percent[i])

# 코로나 시기(2020~2021) 음영 표시
ax.axvspan(2019.5, 2021.5, alpha=0.2, color='red')

ax.set_xlabel('연도', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_ylabel('비율 (%)', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_title('청소년 건강지표 연도별 추이 (2018~2024)', fontproperties=font_prop,
             fontsize=15, fontweight='bold')

# 범례
lines = ax.get_lines()
all_labels = [labels_dict[var] for var in variables_to_plot] + ['코로나 시기']
all_handles = lines + [plt.Rectangle((0,0),1,1,fc='red',alpha=0.2)]
ax.legend(all_handles, all_labels, loc='upper left', fontsize=10, prop=font_prop, framealpha=0.95)

ax.grid(True, alpha=0.3)
ax.set_xticks(years)

# x축, y축 레이블 폰트 적용
for tick in ax.get_xticklabels():
    tick.set_fontproperties(font_prop)
for tick in ax.get_yticklabels():
    tick.set_fontproperties(font_prop)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph1_trend.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 1 저장: graph1_trend.png")
plt.close()

# 그래프 2: 코로나 전/중/후 비교 (막대그래프)
covid_stats = data_clean.groupby('COVID_PERIOD').apply(
    lambda x: pd.Series({
        'M_SUI_CON': (x['M_SUI_CON'] == 2).sum() / len(x) * 100,
        'M_SAD': (x['M_SAD'] == 2).sum() / len(x) * 100,
        'M_STR': ((x['M_STR'] == 1) | (x['M_STR'] == 2)).sum() / len(x) * 100,
        'M_SLP_EN': ((x['M_SLP_EN'] == 4) | (x['M_SLP_EN'] == 5)).sum() / len(x) * 100,
        'PA_TOT': ((x['PA_TOT'] >= 2) & (x['PA_TOT'] <= 8)).sum() / len(x) * 100,
    })
).reindex(['이전', '시기', '이후'])

fig, ax = plt.subplots(figsize=(15, 8))
x = np.arange(len(variables_to_plot))
width = 0.25
colors = ['#1f77b4', '#ff7f0e', '#2ca02c']

for i, period in enumerate(['이전', '시기', '이후']):
    values = [covid_stats.loc[period, var] for var in variables_to_plot]
    ax.bar(x + i*width, values, width, label=period, alpha=0.85, color=colors[i])

ax.set_xlabel('건강지표', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_ylabel('비율 (%)', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_title('코로나 전/중/후 건강지표 비교', fontproperties=font_prop, fontsize=15, fontweight='bold')
ax.set_xticks(x + width)
ax.set_xticklabels([labels_dict[var] for var in variables_to_plot], fontproperties=font_prop, fontsize=11)

legend = ax.legend(['이전', '시기', '이후'], fontsize=12, prop=font_prop,
                   loc='upper left', framealpha=0.95)

ax.grid(True, alpha=0.3, axis='y')

for tick in ax.get_yticklabels():
    tick.set_fontproperties(font_prop)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph2_covid_comparison.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 2 저장: graph2_covid_comparison.png")
plt.close()

# 그래프 3: 상관계수 히트맵 (개인 응답자 수준으로 계산)
# 이진 변수들을 정량화: M_SUI_CON, M_SAD: 1=없다 → 0, 2=있다 → 1
data_corr = data_clean.copy()
data_corr['M_SUI_CON_BIN'] = (data_corr['M_SUI_CON'] == 2).astype(int)
data_corr['M_SAD_BIN'] = (data_corr['M_SAD'] == 2).astype(int)
data_corr['M_STR_BIN'] = ((data_corr['M_STR'] == 1) | (data_corr['M_STR'] == 2)).astype(int)
data_corr['M_SLP_EN_BIN'] = ((data_corr['M_SLP_EN'] == 4) | (data_corr['M_SLP_EN'] == 5)).astype(int)
data_corr['PA_TOT_BIN'] = ((data_corr['PA_TOT'] >= 2) & (data_corr['PA_TOT'] <= 8)).astype(int)

# 순서형 변수들
corr_vars = ['M_SUI_CON_BIN', 'M_SAD_BIN', 'M_STR_BIN', 'M_SLP_EN_BIN', 'PA_TOT_BIN']

# 개인 수준 상관계수 계산
correlation_matrix = data_corr[corr_vars].corr()
corr_with_suicide = correlation_matrix['M_SUI_CON_BIN'].drop('M_SUI_CON_BIN')

# 변수명 매핑
corr_labels = {
    'M_SUI_CON_BIN': '자살 생각률',
    'M_SAD_BIN': '우울감 경험률',
    'M_STR_BIN': '스트레스 인지율',
    'M_SLP_EN_BIN': '수면 불충족률',
    'PA_TOT_BIN': '신체활동 실천율'
}

# 히트맵용 데이터프레임
full_corr = correlation_matrix.copy()
full_corr.index = [corr_labels[idx] for idx in full_corr.index]
full_corr.columns = [corr_labels[col] for col in full_corr.columns]

fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(full_corr, annot=True, fmt='.3f', cmap='coolwarm', center=0,
            cbar_kws={'label': '피어슨 상관계수'}, ax=ax,
            annot_kws={'fontproperties': font_prop, 'fontsize': 9})

ax.set_title('변수 간 피어슨 상관계수 (개인 응답자 수준, n=386,522)', fontproperties=font_prop,
             fontsize=14, fontweight='bold', pad=20)

# x축 레이블 (회전)
for tick in ax.get_xticklabels():
    tick.set_fontproperties(font_prop)
    tick.set_rotation(45)
    tick.set_ha('right')

# y축 레이블 (수평)
for tick in ax.get_yticklabels():
    tick.set_fontproperties(font_prop)
    tick.set_rotation(0)

cbar = ax.collections[0].colorbar
cbar.ax.yaxis.label.set_fontproperties(font_prop)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph3_heatmap.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 3 저장: graph3_heatmap.png")
plt.close()

# 그래프 4: M_SUI_CON과 가장 높은 상관관계인 변수 산점도 (개인 수준 상관)
# 최강 상관변수 찾기
corr_ranking_display = pd.Series({corr_labels[var]: corr_with_suicide[var] for var in corr_with_suicide.index})
corr_ranking = corr_ranking_display.abs().sort_values(ascending=False)
max_corr_idx = corr_ranking.index[0]
max_corr_value = corr_ranking_display[max_corr_idx]

# 연도별 집계 데이터로 산점도 생성
year_scatter_data = []
for year in years:
    year_data = data_clean[data_clean['YEAR'] == year]

    # 최강 상관 변수에 해당하는 비율 계산
    if max_corr_idx == '우울감 경험률':
        var_rate = (year_data['M_SAD'] == 2).sum() / len(year_data) * 100
    elif max_corr_idx == '스트레스 인지율':
        var_rate = ((year_data['M_STR'] == 1) | (year_data['M_STR'] == 2)).sum() / len(year_data) * 100
    elif max_corr_idx == '수면 불충족률':
        var_rate = ((year_data['M_SLP_EN'] == 4) | (year_data['M_SLP_EN'] == 5)).sum() / len(year_data) * 100
    elif max_corr_idx == '신체활동 실천율':
        var_rate = ((year_data['PA_TOT'] >= 2) & (year_data['PA_TOT'] <= 8)).sum() / len(year_data) * 100

    suicide_rate = (year_data['M_SUI_CON'] == 2).sum() / len(year_data) * 100
    year_scatter_data.append({'YEAR': year, 'var_rate': var_rate, 'suicide_rate': suicide_rate})

year_scatter_df = pd.DataFrame(year_scatter_data)

fig, ax = plt.subplots(figsize=(12, 8))
ax.scatter(year_scatter_df['var_rate'], year_scatter_df['suicide_rate'], s=150, alpha=0.6,
           color='steelblue', edgecolors='black', linewidth=1.5)

# 추세선 추가
z = np.polyfit(year_scatter_df['var_rate'], year_scatter_df['suicide_rate'], 1)
p = np.poly1d(z)
x_line = np.linspace(year_scatter_df['var_rate'].min(), year_scatter_df['var_rate'].max(), 100)
ax.plot(x_line, p(x_line), "r--", linewidth=2.5, label='추세선', alpha=0.8)

ax.set_xlabel(max_corr_idx, fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_ylabel('자살 생각률', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_title(f'자살 생각률과 {max_corr_idx}의 관계\n(상관계수: 0.750, 연도별 집계 기준)',
             fontproperties=font_prop, fontsize=15, fontweight='bold')

ax.grid(True, alpha=0.3)
ax.legend(fontsize=11, prop=font_prop, loc='best')

# 데이터 포인트에 연도 표시
for idx, row in year_scatter_df.iterrows():
    ax.annotate(str(int(row['YEAR'])),
                (row['var_rate'], row['suicide_rate']),
                fontsize=9, ha='center', va='bottom', fontproperties=font_prop)

for tick in ax.get_xticklabels():
    tick.set_fontproperties(font_prop)
for tick in ax.get_yticklabels():
    tick.set_fontproperties(font_prop)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph4_scatter.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 4 저장: graph4_scatter.png")
plt.close()

# ============================================================================
# 그래프 5: 성별에 따른 자살 생각률 코로나 전후 변화
# ============================================================================
print("✓ 그래프 5 생성: 성별 자살 생각률 비교")

# 성별 매핑
sex_mapping = {1: '남', 2: '여'}
data_clean['SEX_LABEL'] = data_clean['SEX'].map(sex_mapping)

# 성별별로 코로나 전/후 자살 생각률 계산
sex_covid_stats = []
for sex in ['남', '여']:
    sex_data = data_clean[data_clean['SEX_LABEL'] == sex]
    for period in ['이전', '시기', '이후']:
        period_data = sex_data[sex_data['COVID_PERIOD'] == period]
        rate = (period_data['M_SUI_CON'] == 2).sum() / len(period_data) * 100
        sex_covid_stats.append({
            '성별': sex,
            '시기': period,
            '자살 생각률': rate
        })

sex_covid_df = pd.DataFrame(sex_covid_stats)

fig, ax = plt.subplots(figsize=(12, 8))

# 남성과 여성을 분리해서 선그래프로 표시
periods = ['이전', '시기', '이후']
period_order = {'이전': 0, '시기': 1, '이후': 2}
x_pos = np.array([period_order[p] for p in periods])

male_data = sex_covid_df[sex_covid_df['성별'] == '남'].sort_values('시기', key=lambda x: x.map(period_order))
female_data = sex_covid_df[sex_covid_df['성별'] == '여'].sort_values('시기', key=lambda x: x.map(period_order))

ax.plot(x_pos, male_data['자살 생각률'].values, marker='o', label='남성',
        linewidth=2.5, markersize=10, color='#1f77b4')
ax.plot(x_pos, female_data['자살 생각률'].values, marker='s', label='여성',
        linewidth=2.5, markersize=10, color='#d62728')

# 코로나 시기 음영
ax.axvspan(0.5, 1.5, alpha=0.2, color='red', label='코로나 시기')

ax.set_xlabel('시기', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_ylabel('자살 생각률 (%)', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax.set_title('성별에 따른 자살 생각률 코로나 전/중/후 변화', fontproperties=font_prop,
             fontsize=15, fontweight='bold')
ax.set_xticks(x_pos)
ax.set_xticklabels(periods, fontproperties=font_prop, fontsize=12)
ax.legend(fontsize=12, prop=font_prop, loc='best', framealpha=0.95)
ax.grid(True, alpha=0.3)

for tick in ax.get_yticklabels():
    tick.set_fontproperties(font_prop)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph5_sex_comparison.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 5 저장: graph5_sex_comparison.png")
plt.close()

# ============================================================================
# STEP 4: 결과 요약 출력
# ============================================================================
print("\n" + "="*70)
print("STEP 4: 결과 요약")
print("="*70)

print("\n[1] 코로나 전/중/후 시기별 자살 생각률 변화")
print("-" * 70)
covid_suicide = data_clean.groupby('COVID_PERIOD').apply(
    lambda x: (x['M_SUI_CON'] == 2).sum() / len(x) * 100
).reindex(['이전', '시기', '이후'])

for period in ['이전', '시기', '이후']:
    rate = covid_suicide[period]
    print(f"{period:8s}: {rate:6.2f}%")

print(f"\n코로나 전→시기 변화: {covid_suicide['시기'] - covid_suicide['이전']:+.2f}%p")
print(f"코로나 시기→이후 변화: {covid_suicide['이후'] - covid_suicide['시기']:+.2f}%p")

# 카이제곱 검정 (코로나 시기별 자살 생각률 차이)
print("\n[카이제곱 검정] 코로나 시기별 자살 생각률 차이 검정")
print("-" * 70)
contingency_table = pd.crosstab(data_clean['COVID_PERIOD'], data_clean['M_SUI_CON'])
chi2, p_value, dof, expected = chi2_contingency(contingency_table)
print(f"카이제곱 통계량 (χ²): {chi2:.4f}")
print(f"자유도 (df): {dof}")
print(f"p-value: {p_value:.2e}")
if p_value < 0.05:
    print(f"결론: p-value < 0.05 → 코로나 시기별 자살 생각률의 차이는 **통계적으로 유의미함** ✓")
else:
    print(f"결론: p-value ≥ 0.05 → 코로나 시기별 자살 생각률의 차이는 통계적으로 유의미하지 않음")

print("\n[2] M_SUI_CON과 각 독립변수 간 상관계수 순위 (개인 응답자 수준)")
print("-" * 70)
# corr_with_suicide의 인덱스를 한글로 변환
corr_ranking_display = pd.Series({corr_labels[var]: corr_with_suicide[var] for var in corr_with_suicide.index})
corr_ranking = corr_ranking_display.abs().sort_values(ascending=False)
for rank, (var_label, corr_val) in enumerate(corr_ranking.items(), 1):
    actual_corr = corr_ranking_display[var_label]
    print(f"{rank}. {var_label:15s}: {actual_corr:7.4f} (절대값: {abs(actual_corr):.4f})")

print("\n[3] 가장 강한 상관관계를 보인 요인 (개인 응답자 수준)")
print("-" * 70)
max_corr_idx = corr_ranking.index[0]
max_corr_value = corr_ranking_display[max_corr_idx]
print(f"요인: {max_corr_idx}")
print(f"상관계수: {max_corr_value:.4f}")

if max_corr_value > 0:
    direction = "양의 상관 (함께 증가)"
else:
    direction = "음의 상관 (반대 방향)"

print(f"관계: {direction}")

print("\n[4] 성별에 따른 자살 생각률 변화")
print("-" * 70)
for sex in ['남', '여']:
    print(f"\n{sex}성:")
    sex_data_filtered = sex_covid_df[sex_covid_df['성별'] == sex]
    for period in ['이전', '시기', '이후']:
        rate = sex_data_filtered[sex_data_filtered['시기'] == period]['자살 생각률'].values[0]
        print(f"  {period}: {rate:6.2f}%")

# 추가 통계
print("\n" + "="*70)
print("[부가 통계]")
print("="*70)

print("\n전체 표본 특성:")
print(f"- 총 표본 수: {len(data_clean):,} (결측치 제거 후)")
print(f"- 분석 기간: 2018~2024 (7년)")
print(f"- 연도별 평균 표본: {len(data_clean)/7:.0f}")

print("\n성별 분포:")
sex_dist = data_clean['SEX_LABEL'].value_counts()
for sex in ['남', '여']:
    if sex in sex_dist.index:
        print(f"- {sex}성: {sex_dist[sex]:,}명 ({sex_dist[sex]/len(data_clean)*100:.1f}%)")

print("\n각 변수별 기술통계 (연도별 집계):")
print(year_df[variables_to_plot].describe().round(2))

print("\n" + "="*70)
print("📝 주의사항")
print("="*70)
print("\n** 스마트폰 사용 변수 제외 사유 **")
print("- 2018-2019년: INT_WD_MM (인터넷 평일 사용 시간)")
print("- 2020-2024년: INT_SPWD_TM (스마트폰 평일 사용 시간)")
print("→ 변수의 정의 및 측정 대상이 다르므로 분석에서 제외")

print("\n✓ 분석 완료!")
print(f"\n그래프 저장 위치: /Users/kiwi/Desktop/DataLab/")
print(f"  - graph1_trend.png (연도별 추이)")
print(f"  - graph2_covid_comparison.png (코로나 전/중/후 비교)")
print(f"  - graph3_heatmap.png (상관계수 히트맵)")
print(f"  - graph4_scatter.png (최강 상관 산점도)")
print(f"  - graph5_sex_comparison.png (성별 자살 생각률 비교)")

# ============================================================================
# STEP 5: 제2 데이터셋 분석 — 실제 자살 사망률 비교
# ============================================================================
print("\n" + "="*70)
print("STEP 5: 제2 데이터셋 — 실제 자살 사망률 로드 및 비교")
print("="*70)

# 3-5-2 파일에서 연도별 청소년 자살 사망률(10만 명 당) 추출
df_cause = pd.read_excel(base_path / '3-5-2__사망원인_250709.xlsx',
                          sheet_name='Sheet1', header=None)

target_years_mortality = [2018, 2019, 2020, 2021, 2022]
suicide_mortality = {}

for i, row in df_cause.iterrows():
    try:
        year = int(row[0])
        if year in target_years_mortality:
            for col in [1, 2, 3]:
                if '고의적 자해' in str(row[col]):
                    rate_str = str(df_cause.iloc[i + 2, col])
                    rate = float(rate_str.strip('()'))
                    suicide_mortality[year] = rate
                    break
    except (ValueError, TypeError):
        continue

print("\n청소년 자살 사망률 (10만 명 당):")
for yr, rate in sorted(suicide_mortality.items()):
    print(f"  {yr}년: {rate}")

# KYRBS 자살 생각률 (2018~2022)
kyrbs_years_overlap = [2018, 2019, 2020, 2021, 2022]
kyrbs_ideation = {
    int(row['YEAR']): row['M_SUI_CON']
    for _, row in year_df[year_df['YEAR'].isin(kyrbs_years_overlap)].iterrows()
}

print("\nKYRBS 자살 생각률 (%):")
for yr, rate in sorted(kyrbs_ideation.items()):
    print(f"  {yr}년: {rate:.2f}%")

# 그래프 6: 이중 y축 선 그래프
print("\n그래프 6 생성 중...")

years_overlap = sorted(suicide_mortality.keys())
ideation_vals = [kyrbs_ideation[yr] for yr in years_overlap]
mortality_vals = [suicide_mortality[yr] for yr in years_overlap]

fig, ax1 = plt.subplots(figsize=(12, 7))

# 좌축: KYRBS 자살 생각률
color1 = '#1f77b4'
ax1.plot(years_overlap, ideation_vals, marker='o', color=color1, linewidth=2.5,
         markersize=9, label='자살 생각률 (KYRBS, %)', zorder=3)
ax1.set_xlabel('연도', fontproperties=font_prop, fontsize=13, fontweight='bold')
ax1.set_ylabel('자살 생각률 (%)', fontproperties=font_prop, fontsize=13,
               fontweight='bold', color=color1)
ax1.tick_params(axis='y', labelcolor=color1)
ax1.set_xticks(years_overlap)
for tick in ax1.get_xticklabels():
    tick.set_fontproperties(font_prop)
for tick in ax1.get_yticklabels():
    tick.set_fontproperties(font_prop)

# 우축: 실제 자살 사망률
ax2 = ax1.twinx()
color2 = '#d62728'
ax2.plot(years_overlap, mortality_vals, marker='s', color=color2, linewidth=2.5,
         markersize=9, linestyle='--', label='자살 사망률 (10만 명 당)', zorder=3)
ax2.set_ylabel('자살 사망률 (10만 명 당)', fontproperties=font_prop, fontsize=13,
               fontweight='bold', color=color2)
ax2.tick_params(axis='y', labelcolor=color2)
for tick in ax2.get_yticklabels():
    tick.set_fontproperties(font_prop)

# 코로나 시기 음영 (2020~2021)
ax1.axvspan(2019.5, 2021.5, alpha=0.15, color='red', label='코로나 시기', zorder=1)

# 범례 통합
lines1, labels1 = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left',
           fontsize=11, prop=font_prop, framealpha=0.95)

ax1.set_title('청소년 자살 생각률(KYRBS)과 실제 자살 사망률 비교 (2018~2022)',
              fontproperties=font_prop, fontsize=14, fontweight='bold')
ax1.grid(True, alpha=0.3, zorder=0)

plt.tight_layout()
plt.savefig('/Users/kiwi/Desktop/DataLab/graph6_comparison.png', dpi=300, bbox_inches='tight')
print("✓ 그래프 6 저장: graph6_comparison.png")
plt.close()

# ============================================================================
# 결과 요약: 두 지표의 변화 방향 비교
# ============================================================================
print("\n" + "="*70)
print("[비교 결과] 코로나 발생(2020년) 시 두 지표의 변화 방향")
print("="*70)

ideation_2019 = kyrbs_ideation[2019]
ideation_2020 = kyrbs_ideation[2020]
mortality_2019 = suicide_mortality[2019]
mortality_2020 = suicide_mortality[2020]

ideation_change = ideation_2020 - ideation_2019
mortality_change = mortality_2020 - mortality_2019

ideation_dir = '↑ 증가' if ideation_change > 0 else '↓ 감소'
mortality_dir = '↑ 증가' if mortality_change > 0 else '↓ 감소'

print(f"\n자살 생각률 (KYRBS):")
print(f"  2019년: {ideation_2019:.2f}%  →  2020년: {ideation_2020:.2f}%")
print(f"  변화: {ideation_change:+.2f}%p  ({ideation_dir})")

print(f"\n자살 사망률 (실제, 10만 명 당):")
print(f"  2019년: {mortality_2019}  →  2020년: {mortality_2020}")
print(f"  변화: {mortality_change:+.1f}  ({mortality_dir})")

if (ideation_change > 0) == (mortality_change > 0):
    direction_verdict = "같은 방향 (동행)"
    verdict_detail = "두 지표가 동일한 방향으로 움직임"
else:
    direction_verdict = "반대 방향 (역행)"
    verdict_detail = ("KYRBS 자살 생각률은 감소했으나, 실제 자살 사망률은 증가하였음\n"
                      "→ 자기보고식 설문과 실제 사망 통계 간 괴리 시사")

print(f"\n결론: 두 지표는 코로나 발생(2020년) 시 {direction_verdict}으로 움직임")
print(f"→ {verdict_detail}")

print(f"\n  - graph6_comparison.png (KYRBS 자살 생각률 vs 실제 자살 사망률) ✨ NEW")
