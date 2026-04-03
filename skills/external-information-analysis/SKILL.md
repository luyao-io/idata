---
name: external-information-analysis
description: Manages external information queries including market data, economic indicators, external benchmarks, and GICS industry classifications. Invoke when users ask about market data, external reference information, or industry classifications.
---

# 外部资讯分析

## 概述
用于外部资讯数据分析的数据库模式和业务逻辑，包括市场数据、经济指标、外部基准、GICS行业分类等信息。

## 视图信息

### dtlab_r.v_s081_pdata_ovrssharegicsindustriesclass（GICS行业分类表）
- s_info_sec_code (股票代码)
- gics_ind_code (GICS行业代码)
- s_info_windcode (Wind代码)

### dtlab_r.v_s081_pdata_ashareindustriescode（A股行业代码表）
- industriescode (行业代码)
- industriesname (行业名称)
- industriesalias (行业别名)
- levelnum (层级: 1-5级)

## 业务规则

### 市场数据规则
- **时效性**: 外部资讯数据具有时效性，需关注最新数据
- **基准比较**: 可用于与内部产品表现进行基准比较
- **数据来源**: 区分不同数据提供商的数据质量

### GICS行业分类规则
- **行业层级**: 分为5个层级，从一级到五级
- **分类标准**: 使用全球行业分类标准(GICS)
- **覆盖范围**: 覆盖美股和A股

### 收益率计算规则
- **YTD收益率**: 从年初到当前日期的累计收益率
- **M1/M3/M6收益率**: 近1/3/6个月的收益率
- **Y1收益率**: 近12个月的收益率

## 常用查询示例

### 1. 查询GICS行业分类信息（美股）
```sql
SELECT 'GICS' AS inds_clas,
       A.s_info_sec_code,
       SUBSTR(A.s_info_sec_code, 0, INSTR(A.s_info_sec_code, '.') - 1) AS STOCK_CODE,
       B1.Industriesalias AS INDUSTRIESALIAS1,
       B1.INDUSTRIESNAME AS INDUSTRIESNAME1,
       B2.Industriesalias AS INDUSTRIESALIAS2,
       B2.INDUSTRIESNAME AS INDUSTRIESNAME2,
       B3.Industriesalias AS INDUSTRIESALIAS3,
       B3.INDUSTRIESNAME AS INDUSTRIESNAME3,
       B4.Industriesalias AS INDUSTRIESALIAS4,
       B4.INDUSTRIESNAME AS INDUSTRIESNAME4
FROM dtlab_r.v_s081_pdata_ovrssharegicsindustriesclass A
LEFT JOIN dtlab_r.v_s081_pdata_ashareindustriescode B4
  ON SUBSTR(A.GICS_IND_CODE, 1, 10) = SUBSTR(B4.INDUSTRIESCODE, 1, 10)
  AND B4.LEVELNUM = 5
  AND B4.INDUSTRIESCODE LIKE 'CHG%'
LEFT JOIN dtlab_r.v_s081_pdata_ashareindustriescode B3
  ON SUBSTR(A.GICS_IND_CODE, 1, 8) = SUBSTR(B3.INDUSTRIESCODE, 1, 8)
  AND B3.LEVELNUM = 4
  AND B3.INDUSTRIESCODE LIKE 'CHG%'
LEFT JOIN dtlab_r.v_s081_pdata_ashareindustriescode B2
  ON SUBSTR(A.GICS_IND_CODE, 1, 6) = SUBSTR(B2.INDUSTRIESCODE, 1, 6)
  AND B2.LEVELNUM = 3
  AND B2.INDUSTRIESCODE LIKE 'CHG%'
LEFT JOIN dtlab_r.v_s081_pdata_ashareindustriescode B1
  ON SUBSTR(A.GICS_IND_CODE, 1, 4) = SUBSTR(B1.INDUSTRIESCODE, 1, 4)
  AND B1.LEVELNUM = 2
  AND B1.INDUSTRIESCODE LIKE 'CHG%'
```

### 2. 查询经济指标数据
```sql
SELECT 
    econ_ind_nm as 经济指标名称,
    econ_ind_val as 经济指标值,
    pub_dt as 发布日期,
    unit as 单位
FROM dtlab_r.v_ext_econ_indicators
WHERE econ_ind_nm IN ('GDP增长率', 'CPI', 'PPI', '利率')
  AND freq = 'M'  -- 月度数据
ORDER BY pub_dt DESC, econ_ind_nm
```

### 3. 查询中证指数PE估值数据
```sql
SELECT t.trade_dt as 交易日期,
       t.s_info_windcode as 指数Wind代码,
       b.s_info_compname as 指数全称,
       b.s_info_name as 指数简称,
       t.csi_his_rollpe as 指数滚动市盈率_历史样本_剔亏,
       t.csi_his_rollpe_percentile_fy as 指数近5年滚动市盈率分位数_历史样本_剔亏,
       t.csi_cur_rollpe as 指数滚动市盈率_最新样本_剔亏,
       t.csi_cur_rollpe_percentile_fy as 指数近5年滚动市盈率分位数_最新样本_剔亏
FROM (select *,
             row_number() over (partition by s_info_windcode order by trade_dt desc) as order_num
      from dtlab_r.v_s081_pdata_aindexcsirollpe_b22) t
inner join dtlab_r.v_s081_pdata_aindexdescription_b13 b on t.s_info_windcode = b.s_info_windcode
where t.s_info_windcode in ('931866.CSI', '950357.CSI', '000300.CSI', '000905.CSI')
  and t.order_num <= 10  -- 最近10个有效交易日
```

### 4. 查询多指数对比数据
```sql
-- 查询多个指数的市场表现对比
SELECT 
    mkt_dt as 市场日期,
    mkt_idx_nm as 指数名称,
    idx_val as 指数值,
    chg_pct as 涨跌幅,
    ytd_rt as 今年以来收益率,
    y1_rt as 近一年收益率
FROM dtlab_r.v_ext_mkt_data m
LEFT JOIN dtlab_r.v_ext_bmk_idx b ON m.mkt_idx_nm = b.bmk_idx_nm AND m.mkt_dt = b.calc_dt
WHERE m.mkt_idx_nm IN ('沪深300', '中证500', '创业板指', '上证50', '科创50')
  AND m.mkt_dt >= CURRENT_DATE - INTERVAL '30' DAY
ORDER BY m.mkt_dt DESC, m.mkt_idx_nm
```

### 5. 查询行业估值对比
```sql
-- 查询不同行业的估值水平
SELECT 
    SUBSTR(A.GICS_IND_CODE, 1, 4) as 行业代码,
    B1.INDUSTRIESNAME as 行业名称,
    AVG(t.csi_cur_rollpe) as 平均市盈率,
    COUNT(*) as 成分股数量
FROM dtlab_r.v_s081_pdata_ovrssharegicsindustriesclass A
LEFT JOIN dtlab_r.v_s081_pdata_ashareindustriescode B1
  ON SUBSTR(A.GICS_IND_CODE, 1, 4) = SUBSTR(B1.INDUSTRIESCODE, 1, 4)
  AND B1.LEVELNUM = 2
  AND B1.INDUSTRIESCODE LIKE 'CHG%'
LEFT JOIN dtlab_r.v_s081_pdata_aindexcsirollpe_b22 t
  ON A.s_info_windcode = t.s_info_windcode
WHERE t.trade_dt >= CURRENT_DATE - INTERVAL '5' DAY
GROUP BY SUBSTR(A.GICS_IND_CODE, 1, 4), B1.INDUSTRIESNAME
ORDER BY 平均市盈率 DESC
```