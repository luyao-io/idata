---
name: orgn-cstm-prft-skill
  
description: 用于分析机构客户盈利数据的技能，基于dtlab_r.v_t_orgn_cstm_prft_dat视图，支持客户类型分析、渠道分析、收益权重计算等营销管理分析场景。
---

# 机构客户盈利数据分析

## 视图信息

### dtlab_r.v_t_orgn_cstm_prft_dat（机构客户盈利数据表）
此视图包含机构客户的盈利数据，用于分析客户类型、渠道信息、收益权重等。

## 常用字段说明

- `clnd_dt` (自然日期)
- `crm_bsns_typ` (CRM业务类型)
- `cstm_typ` (客户类型)
- `crm_cstm_nm` (CRM客户名称)
- `fnd_acct` (基金账户)
- `trd_acct` (交易账户)
- `chnn_cd` (渠道代码)
- `chnn_abbr` (渠道简称)
- `prod_cd` (产品代码)
- `prod_abbr` (产品简称)
- `mn_prod_cd` (母产品代码)
- `mn_prod_nm` (母产品名称)
- `prod_typ_203427` (产品类型)
- `tdy_hld_amnt` (今日持有金额)
- `syqz` (收益权重)
- `crm_cstm_typ_lvl_2` (CRM客户类型二级) - 用于精确区分客户子类型，如银行理财子公司

## 业务规则

### 客户类型分类
- 机构客户: `crm_bsns_typ = '机构'`
- 渠道客户: `crm_bsns_typ = '渠道'`
- 银行理财子公司: `crm_cstm_typ_lvl_2 = '银行理财子'`

### 产品类型
- 公募基金: `prod_typ_203427 = '公募'`

### 收益权重
- 收益权重计算: `case when syqz is null then 1 else syqz/100 end`

### 日均保有金额计算
- 日均保有金额 = `sum(tdy_hld_amnt * 收益权重) / (DATEDIFF('day', 开始日期, 结束日期) + 1)`

### 保有规模时点值规则
- 保有规模是个时点值，通常使用区间的最后一天的时点值。在查询特定时间段的保有规模时，应选择该时间段最后一天的数据作为代表值，而非对整个时间段进行平均或其他聚合计算。
- 重要：当分析某个月、某个季度或某个年度的保有规模时，应使用该 period 的最后一天数据，例如：
  - 分析2024年第一季度保有规模，应使用2024-03-31的数据
  - 分析2024年3月保有规模，应使用2024-03-31的数据
  - 分析2024年保有规模，应使用2024-12-31的数据

## 常用查询示例

### 1. 按客户类型分析保有金额
```sql
select
  crm_bsns_typ as 客户业务类型,
  cstm_typ as 客户类型,
  sum(tdy_hld_amnt) as 总保有金额
from
  dtlab_r.v_t_orgn_cstm_prft_dat
where
  clnd_dt = '2024-12-31'
group by
  crm_bsns_typ, cstm_typ
```

### 2. 渠道客户分析
```sql
select
  chnn_abbr as 渠道简称,
  count(distinct fnd_acct) as 账户数,
  sum(tdy_hld_amnt) as 总保有金额
from
  dtlab_r.v_t_orgn_cstm_prft_dat
where
  clnd_dt = '2024-12-31'
  and crm_bsns_typ = '渠道'
group by
  chnn_abbr
order by
  总保有金额 desc
```

### 3. 机构客户按规模分层分析
```sql
select
  crm_cstm_nm as 客户名称,
  sum(tdy_hld_amnt) as 保有金额,
  case
    when sum(tdy_hld_amnt) >= 100000000 then '超大型客户(>=1亿)'
    when sum(tdy_hld_amnt) >= 50000000 then '大型客户(5000万-1亿)'
    when sum(tdy_hld_amnt) >= 10000000 then '中型客户(1000万-5000万)'
    when sum(tdy_hld_amnt) >= 1000000 then '小型客户(100万-1000万)'
    else '微型客户(<100万)'
  end as 客户规模分层
from
  dtlab_r.v_t_orgn_cstm_prft_dat
where
  clnd_dt = '2024-12-31'
  and crm_bsns_typ = '机构'
group by
  crm_cstm_nm
order by
  保有金额 desc
```

### 4. 计算加权保有金额
```sql
select
  crm_cstm_nm as 客户名称,
  prod_abbr as 产品简称,
  sum(tdy_hld_amnt * (case when syqz is null then 1 else syqz/100 end)) as 加权保有金额
from
  dtlab_r.v_t_orgn_cstm_prft_dat
where
  clnd_dt between '2024-01-01' and '2024-12-31'
  and prod_typ_203427 = '公募'
group by
  crm_cstm_nm, prod_abbr
```

### 5. 银行理财子公司公募基金保有分析
```sql
select
  crm_cstm_nm as 客户名称,
  sum(tdy_hld_amnt) as 公募基金保有金额
from
  dtlab_r.v_t_orgn_cstm_prft_dat
where
  clnd_dt = '2024-12-31'
  and crm_cstm_typ_lvl_2 = '银行理财子'
  and prod_typ_203427 = '公募'
group by
  crm_cstm_nm
order by
  公募基金保有金额 desc
```

## 使用场景

### 场景 1：客户类型分析
**目标**：分析机构与渠道客户的保有金额分布情况

**方法**：
1. 使用`crm_bsns_typ`字段区分客户类型
2. 按客户类型分组统计保有金额

### 场景 2：渠道效益分析
**目标**：分析各销售渠道的客户数量和保有金额贡献

**方法**：
1. 筛选`crm_bsns_typ = '渠道'`的数据
2. 按`chnn_abbr`分组统计账户数和保有金额

### 场景 3：高价值客户识别
**目标**：识别保有金额超过特定阈值的高价值客户

**方法**：
1. 按客户名称分组计算总保有金额
2. 设置金额阈值进行客户筛选

### 场景 4：产品盈利分析
**目标**：分析不同产品的加权保有金额情况

**方法**：
1. 使用收益权重计算加权保有金额
2. 按产品分组统计

### 场景 5：银行理财子公司分析
**目标**：分析银行理财子公司的公募基金保有情况

**方法**：
1. 使用`crm_cstm_typ_lvl_2 = '银行理财子'`精确筛选银行理财子公司
2. 筛选`prod_typ_203427 = '公募'`的公募基金产品
3. 按客户名称分组统计保有金额