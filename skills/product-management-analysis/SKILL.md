---
name: product-management-analysis
description: Handles product management analysis queries including fund products, classifications, performance metrics, and asset allocation. Invoke when users ask about product-specific data, fund characteristics, or product classification.
---

# 产品管理分析

## 概述
用于产品管理数据分析的数据库模式和业务逻辑，包括基金产品、产品分类、产品状态、资产配置等信息。

## 视图信息

### dtlab_r.v_dim_prod_dmns（产品维度表）
- prod_srrg_key (产品代理键（产品代码+产品层级）, PRIMARY KEY)
- prod_lvl (产品层级, 0:组合级别 1:份额级别)
- uppr_prod_srrg_key (上级产品代理键, FOREIGN KEY -> dtlab_r.v_dim_prod_dmns)
- prod_nm (产品名称)
- prod_cd (产品代码)
- prod_chn_fll_nm_60001 (产品全称)
- prod_chn_abbr_intr_use_200136 (产品简称)
- prod_typ_203427 (产品类型: 公募/私募)
- prod_typ_200272 (产品类型: 货币/非货币)
- prod_stt_cd_200282 (产品状态代码: 8-运作开放, 7-运作封闭)
- ta_cd (TA代码)
- nav_dt (净值日期)
- mn_prod_cd (母产品代码)
- mn_prod_nm (母产品名称)



## 业务规则

### 产品分类规则
- **公募基金**: prod_typ_203427 = '公募'
- **货币基金**: prod_typ_200272 = '货币'
- **非货币基金**: prod_typ_200272 != '货币'

### 产品状态规则
- **运作开放**: prod_stt_cd_200282 = '8'
- **运作封闭**: prod_stt_cd_200282 = '7'

### 产品层级规则
- **组合级别**: prod_lvl = 0 (母基金)
- **份额级别**: prod_lvl = 1 (子基金)

### 数据单位规则
- **金额单位**: 默认为人民币元
- **份额单位**: 份，保留到小数点后2位
- **净值单位**: 元，保留到小数点后4位

### 查询最佳实践
1. 先按产品类型过滤
2. 再按产品状态过滤
3. 最后按时间范围过滤
4. 优先使用代理键关联

## 常用查询示例

### 1. 查询产品基本信息
```sql
SELECT 
    prod_nm as 产品名称,
    prod_cd as 产品代码,
    prod_typ_203427 as 产品类型,
    prod_typ_200272 as 子类型,
    prod_stt_cd_200282 as 产品状态,
    prod_lvl as 产品层级
FROM dtlab_r.v_dim_prod_dmns
WHERE prod_stt_cd_200282 = '8'  -- 运作开放
```

### 2. 查询公募基金清单
```sql
SELECT 
    prod_chn_fll_nm_60001 as 产品全称,
    prod_chn_abbr_intr_use_200136 as 产品简称,
    prod_cd as 产品代码,
    ta_cd as TA代码
FROM dtlab_r.v_dim_prod_dmns
WHERE prod_typ_203427 = '公募'  -- 公募基金
  AND prod_stt_cd_200282 = '8'  -- 运作开放
ORDER BY prod_cd
```

## 3. 查询所有类型为QDII且属于公募基金的产品代码、产品层级、产品渠道简称以及份额货币。
- `prod_typ_200272='QDII'`: 筛选出产品类型为QDII的产品。
- `prod_typ_203427='公募'`: 进一步筛选出属于公募基金的产品。

## SQL查询
```sql
select 
    prod_cd, prod_lvl,
    prod_chns_abbr_rglt_rprt_60011,
    shr_crrn
from dtlab_r.v_dim_prod_dmns
where prod_typ_200272='QDII'
and prod_typ_203427='公募'
```

