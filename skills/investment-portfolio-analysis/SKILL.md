---
name: investment-portfolio-analysis
description: 用于投研数据分析的数据库模式和业务逻辑，包括单位净值、基金份额、资产配置等产品数据。Invoke when users ask about fund performance, asset allocation, or investment portfolio analysis.
---

# 投资研究数据分析

## 视图信息

### dtlab_r.v_dws_inv_prod_indx_n1（产品指标表_N1）
- prod_srrg_key (产品代理键（产品代码+产品层级）,PRIMARY KEY,FOREIGN KEY -> dtlab_r.v_dim_prod_dmns)
- prod_lvl (产品层级,0:组合级别 1：份额级别)
- prod_cd (产品代码)
- indx_nm (指标名称)
- indx_vl (指标值)
- dt (日期)

### dtlab_r.v_dim_prod_dmns（产品维度表）
- prod_srrg_key (产品代理键)
- prod_cd (产品代码)
- prod_nm (产品名称)
- prod_chn_fll_nm_60001 (产品全称)
- prod_chn_abbr_intr_use_200136 (产品简称)
- prod_typ_203427 (产品类型: 公募/养老金)
- prod_lvl (产品层级)

### dtlab_r.v_t_mohrss_ctgr_asst_attr（人社部资产分类表）
- prod_srrg_key (产品代理键)
- attr_tmpl_name (属性模板名称)
- asst_mppn_rltn_l3 (资产名称)
- end_mkt_size (持有市值)
- end_mkt_position (占基金净值比)
- end_dt (结束日期)
- freq (频率)

## 关键业务指标

### 收益率指标
- **今年以来产品复合收益率增长率01**: 产品年初至今的累计收益率
- **近一年产品复合收益率增长率01**: 最近12个月的收益率
- **近三年产品复合收益率增长率01**: 最近36个月的收益率
- **成立以来产品复合收益率增长率01**: 产品成立以来的累计收益率

### 产品分类
- **公募基金**: prod_typ_203427 = '公募'
- **私募基金**: prod_typ_203427 = '私募'
- **组合级别**: prod_lvl = 0 (母基金)
- **份额级别**: prod_lvl = 1 (子基金)

## 业务规则

### 母子产品关系
- **组合产品**: mn_prod_cd + mn_prod_nm，上级产品（母基金）
- **份额产品**: prod_cd + prod_nm，下级产品（子基金）
- **关联关系**: 通过uppr_prod_srrg_key建立母子关系

### 资产配置规则
- **人社部资产分类**: attr_tmpl_name = '标准人社归因'
- **频率设置**: freq IN ('MTD') 表示月度数据
- **资产配平**: 所有资产需配平，确保资产配置总和为100%

## 常用查询示例

### 1. 查询产品收益率排名
```sql
SELECT 
    a2.prod_chn_fll_nm_60001 as 产品全称,
    a2.prod_chn_abbr_intr_use_200136 as 产品简称,
    a1.prod_cd as 产品代码,
    a1.indx_vl as 指标值,
    a1.dt as 日期
FROM dtlab_r.v_dws_inv_prod_indx_n1 a1
INNER JOIN dtlab_r.v_dim_prod_dmns a2 ON a2.prod_typ_203427 IN ('公募') AND a1.prod_srrg_key = a2.prod_srrg_key
WHERE a1.indx_nm IN ('今年以来产品复合收益率增长率01')
  AND a1.dt = '20211230'
ORDER BY a1.indx_vl DESC
LIMIT 1
```

### 2. 查询产品资产配置情况
```sql
SELECT 
    a30.prod_chn_fll_nm_60001 as 产品名称,
    a10.end_dt as 日期,
    a10.asst_mppn_rltn_l3 as 资产名称,
    a10.end_mkt_size as 持有市值,
    a10.end_mkt_position as 占基金净值比
FROM dtlab_r.v_t_mohrss_ctgr_asst_attr a10
LEFT JOIN dtlab_r.v_dim_prod_dmns a30 ON a10.prod_srrg_key = a30.prod_srrg_key
WHERE a10.attr_tmpl_name IN ('标准人社归因')
  AND a10.freq IN ('MTD')
  AND a10.end_dt BETWEEN '20250520' AND '20250522'
  AND a10.prod_cd IN ('10A002', '10B005')
```

### 3. 查询产品持仓债券明细（含评级信息）
```sql
SELECT a10.prod_cd AS "基金代码"
      ,a10.prod_chn_fll_nm_60001 AS "基金名称"
      ,a10.bnd_scrt_wind_cd AS "债券编号"
      ,a10.bnd_scrt_chn_abbr AS "债券名称"
      ,a10.fnct_crrn_hldn_mkt_vl AS "市值"
      ,a10.hldn_qntt AS "数量"
      ,a10.hldn_cst_fnct_crrn AS "成本"
      ,a10.fnct_crrn_mkt_vl_rt AS "占基金净值比例"
      ,a10.wind_nwst_dbt_rtng AS "债项评级（万得最新）"
      ,a10.wind_mn_rtng AS "主体评级（万得主体）"
      ,a10.vl_dt AS "起息日期"
      ,a10.mtrt_dt AS "到期日期"
      ,a10.cpn_rt AS "票面利率"
      ,a10.intr_dbt_rtng AS "内部债项评级"
      ,a10.intr_mn_rtng AS "内部主体评级"
      ,a10.rskm_dbt_rtng AS "外部债项评级"
      ,a10.rskm_mn_rtng AS "外部主体评级"
      ,a10.mdfd_drtn AS "修正久期"
      ,a10.rsdl_mtrt_yr AS "剩余期限（年）"
  FROM dtlab_r.v_dwm_inv_prod_invs_bnd_hldn_dtls a10
 WHERE a10.prod_cd = '000107' AND
       a10.vltn_dt = '20241212'
 ORDER BY a10.fnct_crrn_mkt_vl_rt DESC
```

### 4. 查询产品持仓股票明细（含行业分类）
```sql
SELECT a10.prod_cd as "基金代码"
       ,a10.prod_chn_fll_nm_60001 AS "基金名称"
       ,coalesce(a10.stck_scrt_wind_cd,a20.scrt_cd) AS "股票代码"
       ,a10.stck_scrt_chn_abbr AS "股票名称"
       ,a10.fnct_crrn_hldn_mkt_vl AS "市值"
       ,a10.hldn_qntt AS "数量"
       ,a10.hldn_cst_fnct_crrn AS "成本"
       ,a10.fnct_crrn_mkt_vl_rt AS "占基金净值比例"
       ,coalesce(a10.wind_lvl_2_inds_nm, a10.wind_lvl_1_inds_nm) AS "万得二级分类"
       ,coalesce(a10.sw_lvl_1_inds_nm,'')||coalesce('--'||a10.sw_lvl_2_inds_nm,'')||coalesce('--'||a10.sw_lvl_3_inds_nm,'') AS "申万行业名称"
       ,coalesce(a10.csrc_lvl_1_inds_nm,'')||coalesce('--'||a10.csrc_lvl_2_inds_nm,'')||coalesce('--'||a10.csrc_lvl_3_inds_nm,'') AS "证监会行业名称"
       ,a10.frst_buy_dt AS "首次买入日期"
       ,a10.rcnt_buy_dt AS "最近买入日期"
   FROM dtlab_r.v_dwm_inv_prod_invs_stck_hldn_dtls a10
   LEFT JOIN dtlab_r.v_dim_scrt_dmns a20
      ON a10.stck_scrt_srrg_key=a20.scrt_srrg_key
 WHERE a10.vltn_dt= '20241212' and
       a10.prod_cd = '000029'
 ORDER BY a10.fnct_crrn_mkt_vl_rt DESC
```

### 5. 查询产品持仓期货明细
```sql
SELECT a10.vltn_dt as "日期"
      ,a10.prod_cd as "产品代码"
      ,a10.prod_chn_fll_nm_60001 as "产品名称"
      ,a20.scrt_cd as "期货代码"
      ,a10.fut_scrt_chn_abbr as "期货名称"
      ,SUM(a10.fnct_crrn_hldn_mkt_vl) AS "持有市值（元）"
      ,SUM(a10.fnct_crrn_mkt_vl_rt) * 100 AS "占基金净值比"
  FROM dtlab_r.v_dwm_inv_prod_invs_fut_hldn_dtls a10
  LEFT JOIN dtlab_r.v_dim_scrt_dmns a20
    ON a10.scrt_srrg_key = a20.scrt_srrg_key
 WHERE a10.vltn_dt BETWEEN '20250501' AND '20250501' AND
       a10.prod_cd IN ('001641','008367','015889')
 GROUP BY a10.vltn_dt
      ,a10.prod_cd
      ,a10.prod_chn_fll_nm_60001
      ,a20.scrt_cd
      ,a10.fut_scrt_chn_abbr
```