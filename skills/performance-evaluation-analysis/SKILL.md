---
name: performance-evaluation-analysis
description: Manages performance evaluation queries including fund returns, risk metrics, and comparative analysis. Invoke when users ask about performance data, fund comparisons, or performance rankings.
---

# 绩效评估分析

## 概述
用于绩效评估数据分析的数据库模式和业务逻辑，包括收益率、风险指标、业绩比较、产品排名等信息。

## 视图信息

### dtlab_r.v_dws_inv_prod_indx_n1（产品指标表_N1）
- prod_srrg_key (产品代理键（产品代码+产品层级）, PRIMARY KEY, FOREIGN KEY -> dtlab_r.v_dim_prod_dmns)
- prod_lvl (产品层级, 0:组合级别 1:份额级别)
- prod_cd (产品代码)
- indx_nm (指标名称)
- indx_vl (指标值)
- stat_dt (统计日期)

### dtlab_r.v_dim_prod_dmns（产品维度表）
- prod_srrg_key (产品代理键)
- prod_cd (产品代码)
- prod_nm (产品名称)
- prod_chn_fll_nm_60001 (产品全称)
- prod_chn_abbr_intr_use_200136 (产品简称)
- prod_typ_203427 (产品类型: 公募/私募)
- prod_typ_200272 (产品类型: 货币/非货币)

## 关键绩效指标

### 收益率指标
- **成立以来产品复合收益率增长率01**: 产品成立以来累计收益率
- **今年以来产品复合收益率增长率01**: 今年年初至今收益率
- **近一年产品复合收益率增长率01**: 最近12个月收益率
- **近三年产品复合收益率增长率01**: 最近36个月收益率
- **近六个月产品复合收益率增长率01**: 最近6个月收益率
- **近三个月产品复合收益率增长率01**: 最近3个月收益率

### 产品分类
- **公募基金**: prod_typ_203427 = '公募'
- **货币基金**: prod_typ_200272 = '货币'
- **非货币基金**: prod_typ_200272 != '货币'

## 业务规则

### 收益率计算规则
- **计算基础**: 基于复权单位净值计算
- **时间范围**: 根据stat_dt字段确定统计期间
- **比较基准**: 可与同类产品或基准指数比较
- **产品层级**: 支持组合级别和份额级别分析

### 绩效评估规则
- **排名规则**: 按收益率从高到低排序
- **时间一致性**: 确保比较的产品使用相同的统计日期
- **产品筛选**: 可按产品类型、状态等条件筛选

## 常用查询示例

### 1. 查询产品收益率排名（今年以来）
```sql
SELECT 
    p.prod_chn_fll_nm_60001 as 产品全称,
    p.prod_chn_abbr_intr_use_200136 as 产品简称,
    p.prod_cd as 产品代码,
    i.indx_vl as 收益率,
    i.stat_dt as 统计日期
FROM dtlab_r.v_dws_inv_prod_indx_n1 i
JOIN dtlab_r.v_dim_prod_dmns p ON i.prod_srrg_key = p.prod_srrg_key
WHERE i.indx_nm = '今年以来产品复合收益率增长率01'
  AND i.stat_dt = (SELECT MAX(stat_dt) FROM dtlab_r.v_dws_inv_prod_indx_n1 WHERE indx_nm = '今年以来产品复合收益率增长率01')
  AND p.prod_typ_203427 = '公募'  -- 公募基金
ORDER BY i.indx_vl DESC
LIMIT 10
```

### 2. 查询产品历史收益率趋势
```sql
SELECT 
    p.prod_chn_fll_nm_60001 as 产品全称,
    i.stat_dt as 统计日期,
    i.indx_vl as 收益率,
    i.indx_nm as 指标名称
FROM dtlab_r.v_dws_inv_prod_indx_n1 i
JOIN dtlab_r.v_dim_prod_dmns p ON i.prod_srrg_key = p.prod_srrg_key
WHERE i.indx_nm IN ('今年以来产品复合收益率增长率01', '近一年产品复合收益率增长率01')
  AND p.prod_nm LIKE '%特定产品%'
  AND i.stat_dt >= '2024-01-01'
ORDER BY i.stat_dt DESC, i.indx_nm
```

### 3. 查询不同时间段的收益率对比
```sql
SELECT 
    p.prod_chn_fll_nm_60001 as 产品全称,
    MAX(CASE WHEN i.indx_nm = '今年以来产品复合收益率增长率01' THEN i.indx_vl END) as 今年以来收益率,
    MAX(CASE WHEN i.indx_nm = '近一年产品复合收益率增长率01' THEN i.indx_vl END) as 近一年收益率,
    MAX(CASE WHEN i.indx_nm = '近三年产品复合收益率增长率01' THEN i.indx_vl END) as 近三年收益率
FROM dtlab_r.v_dws_inv_prod_indx_n1 i
JOIN dtlab_r.v_dim_prod_dmns p ON i.prod_srrg_key = p.prod_srrg_key
WHERE i.indx_nm IN ('今年以来产品复合收益率增长率01', '近一年产品复合收益率增长率01', '近三年产品复合收益率增长率01')
  AND i.stat_dt = (SELECT MAX(stat_dt) FROM dtlab_r.v_dws_inv_prod_indx_n1 WHERE indx_nm IN ('今年以来产品复合收益率增长率01', '近一年产品复合收益率增长率01', '近三年产品复合收益率增长率01'))
  AND p.prod_typ_203427 = '公募'
GROUP BY p.prod_chn_fll_nm_60001
HAVING MAX(CASE WHEN i.indx_nm = '今年以来产品复合收益率增长率01' THEN i.indx_vl END) IS NOT NULL
ORDER BY MAX(CASE WHEN i.indx_nm = '今年以来产品复合收益率增长率01' THEN i.indx_vl END) DESC
LIMIT 20
```

