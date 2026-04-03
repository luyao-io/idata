---
name: marketing-management-analysis
description: 用于营销市场数据分析的数据库模式和业务逻辑，包括交易、保有、申赎、客户持仓、客户行为分析、精准营销等信息。Invoke when users ask about marketing data, customer transactions, fund flows, customer behavior analysis, or precision marketing.
---

# 营销数据分析

## 视图信息

### dtlab_r.v_dws_mkt_all_chnn_trd_indx（全渠道交易指标表）
- ta_cnfr_id (TA确认编号,PRIMARY KEY)
- ta_cd (TA代码,PRIMARY KEY)
- fnd_acct_srrg_key (基金账户代理键（基金账号+TA代码）,FOREIGN KEY -> dtlab_r.v_dim_fnd_acct_dmns_h)
- sll_chnn_srrg_key (销售渠道代理键,FOREIGN KEY -> dtlab_r.v_dim_sll_chnn_dmns)
- prod_srrg_key (产品代理键,FOREIGN KEY -> dtlab_r.v_dim_prod_dmns)
- cstm_srrg_key (客户代理键,FOREIGN KEY -> dtlab_r.v_dim_cstm_dmns_h)
- orgn_crrn_cnfr_amnt (确认金额_本币,单位:元)
- fnd_bsns_typ_cd (基金业务类型代码)
- fnct_crrn_cnfr_amnt (确认金额_功能币)

### dtlab_r.v_dws_mkt_all_chnn_hld_indx（全渠道保有指标表）
- clnd_dt (自然日期,PRIMARY KEY)
- ta_cd (TA代码,PRIMARY KEY)
- fnd_acct_srrg_key (基金账户代理键,PRIMARY KEY,FOREIGN KEY -> dtlab_r.v_dim_fnd_acct_dmns_h)
- trd_acct (交易账号,PRIMARY KEY)
- sll_chnn_srrg_key (销售渠道代理键,PRIMARY KEY,FOREIGN KEY -> dtlab_r.v_dim_sll_chnn_dmns)
- ntwr_cd (网点代码,PRIMARY KEY)
- shr_typ_cd (份额类别代码,PRIMARY KEY)
- prod_srrg_key (产品代理键,PRIMARY KEY,FOREIGN KEY -> dtlab_r.v_dim_prod_dmns)
- cstm_srrg_key (客户代理键,FOREIGN KEY -> dtlab_r.v_dim_cstm_dmns_h)
- shr_blnc (保有份额)
- amnt_blnc_5 (金额余额（原币）)
- amnt_blnc_6 (金额余额（本币）)

### dtlab_r.v_dim_prod_dmns（产品维度表）
- prod_srrg_key (产品代理键)
- prod_cd (产品代码)
- prod_nm (产品名称)
- mn_prod_cd (母产品代码)
- mn_prod_nm (母产品名称)

## 业务类型代码

### 交易类型
- **认购**: fnd_bsns_typ_cd = '130' (基金成立的认购结果)
- **申购**: fnd_bsns_typ_cd IN ('122','139') (包含申购和定期定额申购)
- **赎回**: fnd_bsns_typ_cd IN ('124','142','163') (包含赎回、定期定额赎回和强制赎回)

### 保有指标
- **当前保有金额**: clnd_dt = 指定日期, amnt_blnc_6(保有金额)
- **当前保有份额**: clnd_dt = 指定日期, shr_blnc(保有份额)
- **首次持仓日期**: MIN(clnd_dt) (客户首次持仓日期)

## 业务规则

### 净申赎计算
**净申赎 = (认购 + 申购) - 赎回**

### 产品层级
- **组合级别**: 母产品级别，使用mn_prod_cd和mn_prod_nm
- **份额级别**: 子产品级别，使用prod_cd和prod_nm

### 数据单位
- **金额单位**: 默认为人民币元，除以10000转换为万元
- **份额单位**: 份

## 常用查询示例

### 1. 查询指定申请日期的公募产品申购赎回数据
```sql
SELECT SPLIT_PART(mn_prod_cd, '+', 1) 产品代码,
       mn_prod_nm 产品名称,
       SUM(CASE
               WHEN fnd_bsns_typ_cd IN ('120', '122', '137', '139') THEN
                fnct_crrn_cnfr_amnt / 10000
               ELSE 0
           END) AS '申购（万元）',
       SUM(CASE
               WHEN fnd_bsns_typ_cd IN ('124', '138', '142', '163') THEN
                fnct_crrn_cnfr_amnt / 10000
               ELSE 0
           END) AS '赎回（万元）'
FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx
WHERE fnd_bsns_typ_cd IN ('120', '122', '137', '139', '124', '138', '142', '163')
  AND mn_prod_cd IS NOT NULL
GROUP BY SPLIT_PART(mn_prod_cd, '+', 1), mn_prod_nm
```

### 2. 获取2025年3月份净申赎排名前10的产品（组合级别）
```sql
select c.mn_prod_nm 组合产品名称,
       c.mn_prod_cd 组合产品代码,
       sum(case
             when fnd_bsns_typ_cd in ('130', '122', '139') then
              cnfr_shr
             when fnd_bsns_typ_cd in ('124', '142', '139') then
             - cnfr_shr   
           end) as 净申赎份额,
       sum(case
             when fnd_bsns_typ_cd in ('130', '122', '139') then
              orgn_crrn_cnfr_amnt
             when fnd_bsns_typ_cd in ('124', '142', '163') then
             - orgn_crrn_cnfr_amnt
           end) as 净申赎金额
  from dtlab_r.v_dws_mkt_all_chnn_trd_indx c
 where fnd_bsns_typ_cd in ('130', '122', '139', '124', '142', '163') 
   AND c.cnfr_dt between '20250301' and '20250331'
 GROUP BY c.mn_prod_nm, c.mn_prod_cd
 ORDER BY 净申赎金额 DESC limit 10
;
```
### 3. 获取2025年3月份净申赎排名前10的产品（组合级别）
```sql
 select c.prod_nm 份额产品名称,
        c.prod_cd 份额产品代码,
        sum(case
              when c.clnd_dt = '20240801' then
               shr_blnc
            end) as 期初保有份额,
        sum(case
              when c.clnd_dt = '20240801' then
               amnt_blnc_6
            end) as 期初保有金额,
        sum(case
              when c.clnd_dt = '20240831' then
               shr_blnc
            end) as 期末保有份额,
        sum(case
              when c.clnd_dt = '20240831' then
               amnt_blnc_6
            end) as 期末保有金额
   from dtlab_r.v_dws_mkt_all_chnn_hld_indx c
  where c.clnd_dt between '20240801' and '20240831'
    and prod_cd = '009863'
  GROUP BY c.prod_nm, c.prod_cd
;
```
### 4. 获取日期为20240801的客户的产品保有持仓数据
```sql
select cstm_fll_nm 客户名称,prod_cd 产品代码,prod_nm 产品名称,sum(shr_blnc) as 保有份额,sum(amnt_blnc_6) as 保有金额
   from dtlab_r.v_dws_mkt_all_chnn_hld_indx c
  where c.clnd_dt = '20240801' 
    and cstm_srrg_key = '161'
    group by cstm_fll_nm,prod_cd,prod_nm
```

### 5. 查询产品持有人结构时间序列
```sql
select
a.clnd_dt as 日期,
split_part(a.mn_prod_cd,'+',1) as 主产品代码,
a.mn_prod_nm as 主产品名称,
a.sll_chnn_cd_0 as 渠道代码,
a.sll_chnn_abbr_0 as 渠道名称,
sum(case when a.cstm_typ = '个人' then a.shr_blnc else 0 end) as 个人客户份额,
sum(case when a.cstm_typ = '个人' then a.shr_blnc else 0 end)/nullifzero(sum(a.shr_blnc)) as 个人客户占比,
sum(case when a.cstm_typ in ('机构','产品') then a.shr_blnc else 0 end) as 机构客户份额,
sum(case when a.cstm_typ in ('机构','产品') then a.shr_blnc else 0 end)/nullifzero(sum(a.shr_blnc)) as 机构客户占比
from dtlab_r.v_dws_mkt_all_chnn_hld_indx a
where a.clnd_dt between '2023-09-06' and '2023-09-06'
and split_part(a.mn_prod_cd,'+',1) in ('000638','100025','511900','000602')
group by 1,2,3,4,5
```

### 6. 查询客户交易行为分析
```sql
-- 分析客户近一年主动交易笔数（不含定投）
SELECT 
    cstm_fll_nm as 客户名称,
    SUM(CASE WHEN fnd_bsns_typ_cd IN ('122','137') THEN 1 ELSE 0 END) as 主动申购笔数,
    SUM(CASE WHEN fnd_bsns_typ_cd IN ('124','138') THEN 1 ELSE 0 END) as 主动赎回笔数,
    LEAST(
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('122','137') THEN 1 ELSE 0 END),
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('124','138') THEN 1 ELSE 0 END)
    ) as 主动交易笔数_孰低
FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx
WHERE cnfr_dt >= add_months(current_date, -12)
  AND fnd_bsns_typ_cd IN ('122','137','124','138')  -- 主动申赎，不含定投
  AND prod_typ_200272 != '货币'  -- 非货币基金
GROUP BY cstm_fll_nm

-- 分析客户定投习惯
SELECT 
    cstm_fll_nm as 客户名称,
    SUM(CASE WHEN fnd_bsns_typ_cd = '139' THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 累计定投申购金额,
    SUM(CASE WHEN fnd_bsns_typ_cd = '139' THEN 1 ELSE 0 END) as 定投申购笔数,
    SUM(CASE WHEN fnd_bsns_typ_cd = '163' THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 累计定赎金额,
    SUM(CASE WHEN fnd_bsns_typ_cd = '163' THEN 1 ELSE 0 END) as 定赎笔数
FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx
WHERE cnfr_dt >= add_months(current_date, -12)
  AND fnd_bsns_typ_cd IN ('139','163')  -- 定期定额申赎
GROUP BY cstm_fll_nm
```

### 7. 客户交易活跃度分析
```sql
-- 分析客户近一年交易活跃度（不含定投）
WITH customer_trading AS (
    SELECT 
        cstm_srrg_key,
        cstm_fll_nm,
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('122','137') THEN 1 ELSE 0 END) as 主动申购笔数,
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('124','138') THEN 1 ELSE 0 END) as 主动赎回笔数,
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('122','137') THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 主动申购金额,
        SUM(CASE WHEN fnd_bsns_typ_cd IN ('124','138') THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 主动赎回金额,
        MIN(cnfr_dt) as 首次交易日期,
        MAX(cnfr_dt) as 最后交易日期
    FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx
    WHERE cnfr_dt >= add_months(current_date, -12)
      AND fnd_bsns_typ_cd IN ('122','137','124','138')  -- 主动申赎，不含定投
      AND prod_typ_200272 != '货币'  -- 非货币基金
    GROUP BY cstm_srrg_key, cstm_fll_nm
)
SELECT 
    cstm_fll_nm as 客户名称,
    主动申购笔数,
    主动赎回笔数,
    LEAST(主动申购笔数, 主动赎回笔数) as 主动交易笔数_孰低,
    主动申购金额 / 10000 as 主动申购金额_万元,
    主动赎回金额 / 10000 as 主动赎回金额_万元,
    CASE 
        WHEN 主动交易笔数_孰低 >= 24 THEN '高频交易客户'
        WHEN 主动交易笔数_孰低 >= 12 THEN '中频交易客户'
        WHEN 主动交易笔数_孰低 >= 6 THEN '低频交易客户'
        ELSE '偶尔交易客户'
    END as 交易频率分类,
    DATEDIFF(day, 首次交易日期, 最后交易日期) + 1 as 交易活跃天数,
    ROUND(主动交易笔数_孰低 * 1.0 / NULLIF(DATEDIFF(day, 首次交易日期, 最后交易日期) + 1, 0) * 30, 2) as 月均交易频率
FROM customer_trading
ORDER BY 主动交易笔数_孰低 DESC
```

### 8. 客户定投行为分析
```sql
-- 分析客户定投习惯和偏好
WITH customer_sip AS (
    SELECT 
        cstm_srrg_key,
        cstm_fll_nm,
        SUM(CASE WHEN fnd_bsns_typ_cd = '139' THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 累计定投申购金额,
        SUM(CASE WHEN fnd_bsns_typ_cd = '139' THEN 1 ELSE 0 END) as 定投申购笔数,
        SUM(CASE WHEN fnd_bsns_typ_cd = '163' THEN orgn_crrn_cnfr_amnt ELSE 0 END) as 累计定赎金额,
        SUM(CASE WHEN fnd_bsns_typ_cd = '163' THEN 1 ELSE 0 END) as 定赎笔数,
        AVG(CASE WHEN fnd_bsns_typ_cd = '139' THEN orgn_crrn_cnfr_amnt END) as 平均定投金额,
        MIN(CASE WHEN fnd_bsns_typ_cd = '139' THEN cnfr_dt END) as 首次定投日期,
        MAX(CASE WHEN fnd_bsns_typ_cd = '139' THEN cnfr_dt END) as 最后定投日期
    FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx
    WHERE cnfr_dt >= add_months(current_date, -12)
      AND fnd_bsns_typ_cd IN ('139','163')  -- 定期定额申赎
    GROUP BY cstm_srrg_key, cstm_fll_nm
    HAVING SUM(CASE WHEN fnd_bsns_typ_cd = '139' THEN 1 ELSE 0 END) > 0
)
SELECT 
    cstm_fll_nm as 客户名称,
    累计定投申购金额 / 10000 as 累计定投金额_万元,
    定投申购笔数,
    平均定投金额,
    CASE 
        WHEN 平均定投金额 >= 10000 THEN '大额定投客户'
        WHEN 平均定投金额 >= 5000 THEN '中额定投客户'
        WHEN 平均定投金额 >= 1000 THEN '小额定投客户'
        ELSE '微额定投客户'
    END as 定投金额分类,
    CASE 
        WHEN 定投申购笔数 >= 24 THEN '坚持定投客户'
        WHEN 定投申购笔数 >= 12 THEN '持续定投客户'
        WHEN 定投申购笔数 >= 6 THEN '尝试定投客户'
        ELSE '新手定投客户'
    END as 定投持续性分类,
    DATEDIFF(day, 首次定投日期, 最后定投日期) + 1 as 定投持续天数,
    ROUND(定投申购笔数 * 1.0 / NULLIF(DATEDIFF(day, 首次定投日期, 最后定投日期) + 1, 0) * 30, 2) as 月均定投频率
FROM customer_sip
ORDER BY 累计定投申购金额 DESC
```

### 9. 客户追涨杀跌行为识别
```sql
-- 识别客户的追涨杀跌行为
WITH customer_timing AS (
    SELECT 
        t.cstm_srrg_key,
        t.cstm_fll_nm,
        t.cnfr_dt,
        t.fnd_bsns_typ_cd,
        t.orgn_crrn_cnfr_amnt,
        t.mn_prod_cd,
        nav.indx_vl as 当日净值,
        -- 计算过去20天的净值均值和标准差
        AVG(nav_history.indx_vl) OVER (
            PARTITION BY t.mn_prod_cd 
            ORDER BY t.cnfr_dt 
            ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
        ) as 过去20天平均净值,
        STDDEV(nav_history.indx_vl) OVER (
            PARTITION BY t.mn_prod_cd 
            ORDER BY t.cnfr_dt 
            ROWS BETWEEN 20 PRECEDING AND 1 PRECEDING
        ) as 过去20天净值标准差
    FROM dtlab_r.v_dws_mkt_all_chnn_trd_indx t
    LEFT JOIN dtlab_r.v_dws_inv_prod_indx_n1 nav 
        ON t.mn_prod_cd = nav.prod_cd 
        AND t.cnfr_dt = nav.stat_dt 
        AND nav.indx_nm = '单位净值'
    LEFT JOIN dtlab_r.v_dws_inv_prod_indx_n1 nav_history 
        ON t.mn_prod_cd = nav_history.prod_cd 
        AND nav_history.indx_nm = '单位净值'
    WHERE t.cnfr_dt >= add_months(current_date, -12)
      AND t.fnd_bsns_typ_cd IN ('122','137','124','138')  -- 主动申赎
      AND t.prod_typ_200272 != '货币'  -- 非货币基金
)
SELECT 
    cstm_fll_nm as 客户名称,
    SUM(CASE 
        WHEN fnd_bsns_typ_cd IN ('122','137') AND 
             当日净值 > (过去20天平均净值 + 2.5 * 过去20天净值标准差)
        THEN 1 ELSE 0 
    END) as 追涨次数,
    SUM(CASE 
        WHEN fnd_bsns_typ_cd IN ('124','138') AND 
             当日净值 < (过去20天平均净值 - 2.5 * 过去20天净值标准差)
        THEN 1 ELSE 0 
    END) as 杀跌次数,
    COUNT(*) as 总主动交易次数,
    ROUND((SUM(CASE 
        WHEN fnd_bsns_typ_cd IN ('122','137') AND 
             当日净值 > (过去20天平均净值 + 2.5 * 过去20天净值标准差)
        THEN 1 ELSE 0 
    END) + SUM(CASE 
        WHEN fnd_bsns_typ_cd IN ('124','138') AND 
             当日净值 < (过去20天平均净值 - 2.5 * 过去20天净值标准差)
        THEN 1 ELSE 0 
    END)) * 100.0 / NULLIF(COUNT(*), 0), 2) as 追涨杀跌行为占比,
    CASE 
        WHEN (SUM(CASE 
            WHEN fnd_bsns_typ_cd IN ('122','137') AND 
                 当日净值 > (过去20天平均净值 + 2.5 * 过去20天净值标准差)
            THEN 1 ELSE 0 
        END) + SUM(CASE 
            WHEN fnd_bsns_typ_cd IN ('124','138') AND 
                 当日净值 < (过去20天平均净值 - 2.5 * 过去20天净值标准差)
            THEN 1 ELSE 0 
        END)) * 100.0 / COUNT(*) >= 30 THEN '高追涨杀跌倾向'
        WHEN (SUM(CASE 
            WHEN fnd_bsns_typ_cd IN ('122','137') AND 
                 当日净值 > (过去20天平均净值 + 2.5 * 过去20天净值标准差)
            THEN 1 ELSE 0 
        END) + SUM(CASE 
            WHEN fnd_bsns_typ_cd IN ('124','138') AND 
                 当日净值 < (过去20天平均净值 - 2.5 * 过去20天净值标准差)
            THEN 1 ELSE 0 
        END)) * 100.0 / COUNT(*) >= 15 THEN '中追涨杀跌倾向'
        ELSE '低追涨杀跌倾向'
    END as 追涨杀跌行为分类
FROM customer_timing
WHERE 过去20天平均净值 IS NOT NULL 
  AND 过去20天净值标准差 IS NOT NULL
GROUP BY cstm_fll_nm
HAVING 总主动交易次数 >= 5
ORDER BY 追涨杀跌行为占比 DESC
```

### 9. 客户持仓集中度分析
```sql
-- 分析客户持仓集中度
WITH customer_holding AS (
    SELECT 
        cstm_srrg_key,
        cstm_fll_nm,
        mn_prod_cd,
        mn_prod_nm,
        clnd_dt,
        amnt_blnc_6 as 持仓金额,
        SUM(amnt_blnc_6) OVER (PARTITION BY cstm_srrg_key, clnd_dt) as 总持仓金额,
        RANK() OVER (PARTITION BY cstm_srrg_key, clnd_dt ORDER BY amnt_blnc_6 DESC) as 持仓排名
    FROM dtlab_r.v_dws_mkt_all_chnn_hld_indx
    WHERE clnd_dt = (SELECT MAX(clnd_dt) FROM dtlab_r.v_dws_mkt_all_chnn_hld_indx)
      AND amnt_blnc_6 > 0
)
SELECT 
    cstm_fll_nm as 客户名称,
    COUNT(DISTINCT mn_prod_cd) as 持仓产品数量,
    MAX(总持仓金额) / 10000 as 总持仓金额_万元,
    MAX(CASE WHEN 持仓排名 = 1 THEN mn_prod_nm END) as 第一大持仓产品,
    MAX(CASE WHEN 持仓排名 = 1 THEN 持仓金额 END) / 10000 as 第一大持仓金额_万元,
    ROUND(MAX(CASE WHEN 持仓排名 = 1 THEN 持仓金额 END) * 100.0 / MAX(总持仓金额), 2) as 第一大持仓占比,
    MAX(CASE WHEN 持仓排名 <= 3 THEN 持仓金额 END) / 10000 as 前三大持仓金额_万元,
    ROUND(MAX(CASE WHEN 持仓排名 <= 3 THEN 持仓金额 END) * 100.0 / MAX(总持仓金额), 2) as 前三大持仓占比,
    CASE 
        WHEN MAX(CASE WHEN 持仓排名 = 1 THEN 持仓金额 END) * 100.0 / MAX(总持仓金额) >= 50 THEN '高度集中'
        WHEN MAX(CASE WHEN 持仓排名 <= 3 THEN 持仓金额 END) * 100.0 / MAX(总持仓金额) >= 70 THEN '中度集中'
        ELSE '相对分散'
    END as 持仓集中度分类
FROM customer_holding
GROUP BY cstm_fll_nm
HAVING MAX(总持仓金额) >= 10000  -- 持仓金额大于1万元
ORDER BY 总持仓金额_万元 DESC
```

### 10. 客户持仓时间分析
```sql
-- 分析客户持仓时间长度
WITH customer_first_hold AS (
    SELECT 
        cstm_srrg_key,
        cstm_fll_nm,
        mn_prod_cd,
        MIN(clnd_dt) as 首次持仓日期,
        MAX(clnd_dt) as 最后持仓日期
    FROM dtlab_r.v_dws_mkt_all_chnn_hld_indx
    WHERE shr_blnc > 100  -- 持仓份额大于100份
    GROUP BY cstm_srrg_key, cstm_fll_nm, mn_prod_cd
),
current_holdings AS (
    SELECT 
        cstm_srrg_key,
        mn_prod_cd,
        clnd_dt,
        shr_blnc
    FROM dtlab_r.v_dws_mkt_all_chnn_hld_indx
    WHERE clnd_dt = (SELECT MAX(clnd_dt) FROM dtlab_r.v_dws_mkt_all_chnn_hld_indx)
      AND shr_blnc > 100
)
SELECT 
    cfh.cstm_fll_nm as 客户名称,
    COUNT(DISTINCT cfh.mn_prod_cd) as 历史持仓产品数量,
    COUNT(DISTINCT ch.mn_prod_cd) as 当前持仓产品数量,
    AVG(DATEDIFF(day, cfh.首次持仓日期, COALESCE(ch.clnd_dt, current_date))) as 平均持仓天数,
    MAX(DATEDIFF(day, cfh.首次持仓日期, COALESCE(cfh.最后持仓日期, current_date))) as 最长持仓天数,
    CASE 
        WHEN AVG(DATEDIFF(day, cfh.首次持仓日期, COALESCE(ch.clnd_dt, current_date))) >= 730 THEN '长期投资者'
        WHEN AVG(DATEDIFF(day, cfh.首次持仓日期, COALESCE(ch.clnd_dt, current_date))) >= 365 THEN '中期投资者'
        WHEN AVG(DATEDIFF(day, cfh.首次持仓日期, COALESCE(ch.clnd_dt, current_date))) >= 90 THEN '短期投资者'
        ELSE '超短期投资者'
    END as 投资期限分类
FROM customer_first_hold cfh
LEFT JOIN current_holdings ch 
    ON cfh.cstm_srrg_key = ch.cstm_srrg_key 
    AND cfh.mn_prod_cd = ch.mn_prod_cd
GROUP BY cfh.cstm_fll_nm
HAVING COUNT(DISTINCT cfh.mn_prod_cd) >= 3  -- 至少持有过3个产品
ORDER BY 平均持仓天数 DESC
```
## 使用场景

### 场景 1：分析客户交易情况概况
**目标**：按客户细分计算客户近一年的基金申购和赎回金额，产品范围为非货币基金

**方法**：
1. 使用cnfr_dt >=add_months(date('20260209'),-12)过滤近一年的数据，产品范围prod_typ_200272不等于货币 
2. 应用 fnd_bsns_trd_drct 分类统计买入卖出情况
3. 按月分组，计算各月申购和赎回金额

### 场景 2：分析客户的主动交易风格
**目标**：
1. 主动交易：按客户细分统计近一年主动发起的基金申购和赎回交易笔数，并以两者的孰低者作为近一年的主动交易笔数，定投交易不计入内
2. 追涨杀跌：统计近一年主动发起的基金申购和赎回交易中，是否存在以下情况：
    * 追涨行为：买入确认净值大于过去20天平均净值+2.5个标准差
    * 杀跌行为：卖出确认净值小于过去20天平均净值-2.5个标准差

**方法**：
1. dtlab_r.v_dws_inv_prod_indx_n1（产品指标表_N1）中指标indx_id IN ('drvi_nav_unit_frgn_td_dsclsr_00')获取过去一年20天的单位净值,以及过去20天的平均均值和2.5个标准差
2. 使用cnfr_dt过滤近一年的交易数据,fnd_bsns_typ_cd in ('122','137')(申购,基金转换转入) fnd_bsns_typ_cd in ('124','138')(赎回,基金转换转出) ,关联产品净值,判断买入确认净值和过去20天平均净值加减2.5个标准差的大小


### 3：分析客户定投交易习惯
**目标**：分析客户近一年的发生的累计扣款金额和笔数

**方法**：
1. 使用cnfr_dt过滤近一年的数据
2. fnd_bsns_typ_cd ='139' 定期定额申购 fnd_bsns_typ_cd in ('163') 定期定额赎回


### 4：分析客户基金持有时长
**目标**：统计客户持仓基金中，持有日期最长的三只基金，持有份额数不足100份的持仓基金不计入内
**方法**：
1. 使用shr_blnc >100

### 场景 5：客户精准营销策略制定
**目标**：基于客户行为特征进行客户细分，制定个性化营销策略

**方法**：
1. 使用客户交易活跃度分析识别客户交易频率特征
2. 使用客户定投行为分析识别客户定投习惯和偏好
3. 使用客户追涨杀跌行为识别判断客户投资行为特征
4. 使用客户持仓集中度分析了解客户投资集中度偏好
5. 使用客户持仓时间分析识别客户投资期限特征
6. 综合以上特征进行客户画像和营销策略制定

### 场景 6：营销效果评估分析
**目标**：分析不同客户群体对营销活动的响应度，评估营销效果

**方法**：
1. 建立营销活动数据与交易数据的关联
2. 计算响应率、平均响应交易金额、响应延迟天数等关键指标
3. 基于响应度进行营销效果评价和策略优化