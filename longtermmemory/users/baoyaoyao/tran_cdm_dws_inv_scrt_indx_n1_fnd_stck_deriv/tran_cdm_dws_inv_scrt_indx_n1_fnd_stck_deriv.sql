/***************************************** Head Section *******************************************/
/**  主题 = CDM                                                                                   */
/**  表名 = dws_inv_scrt_indx_n1                                                                     */
/**  作业描述 = 证券指标表_N1（DWS_）                                                             */
/**  开发人员 = jiangcheng                                                                            */
/**  SQL脚本必须 utf-8 格式                                                                       */
/**  预留变量：${TX_DATE_I}                     # 多天批量多次运行使用                            */
/**  预留变量：${START_TX_DATE} ${END_TX_DATE}  # 多天批量一次运行中使用                          */
/**  预留变量：${TX_DATE_BATCH}                                                                   */
/**  预留变量：${ETL_JOB}                                                                         */
/**  预留变量：${$MAXDATE}                                                                        */
/**  预留变量：${$MINDATE}                                                                        */
/**  预留变量：                                                                                   */
/**  预留变量：                                                                                   */
/*************************************** Head Section End *****************************************/

/*-FOR=N*/
DROP TABLE IF EXISTS tmp_dws_inv_scrt_indx_n1 CASCADE;
CREATE LOCAL TEMP TABLE tmp_dws_inv_scrt_indx_n1 ON COMMIT PRESERVE ROWS AS
SELECT 		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
  FROM ${CDM_SCHEMA}.dws_inv_scrt_indx_n1
 WHERE 1 <> 1;
/*-ENDFOR*/


/*-FOR=N*/
DROP TABLE IF EXISTS t_fnd_scrt_qtr_indx_privalue; 
CREATE LOCAL TEMP TABLE t_fnd_scrt_qtr_indx_privalue ON COMMIT PRESERVE ROWS AS 
SELECT a10.s_info_windcode /* 基金代码 */
      ,a10.s_info_investwindcode AS s_info_stockwindcode /*该字段非主键，会有重复数据,手工剔除*/
      ,a10.investcode
      ,a10.name                  AS investname
      ,a20.main_code
      ,a10.value                 AS f_prt_stkvalue /* 持有股票市值(元) */
      ,a10.posstktonav           AS f_prt_stkvaluetonav /* 持有股票市值占基金净值比例(%) */
      ,a10.enddate               AS f_prt_enddate /* 截止日期 */
  FROM ${DL_ODS_INFO_SCHEMA}.s081_pdata_qdiisecuritiesportfolio_b04 a10
 INNER JOIN ${DL_ODS_INFO_SCHEMA}.s081_pdata_chinamutualfunddescription a20
    ON a10.s_info_windcode = a20.f_info_windcode AND
       a20.f_info_setupdate IS NOT NULL AND
       a20.f_info_maturitydate IS NULL AND
       a20.f_info_isinitial = '1'
 INNER JOIN ${DL_ODS_INFO_SCHEMA}.s081_pdata_cmfbalancesheet a30 
    on a30.s_info_windcode = a10.s_info_windcode and a10.enddate = a30.report_period
 WHERE a10.type = '股票' 
union all
SELECT a10.s_info_windcode /* 基金代码 */
      ,a10.s_info_stockwindcode
      ,NULL                     AS investcode
      ,NULL                     AS NAME
      ,a20.main_code
      ,a10.f_prt_stkvalue /* 持有股票市值(元) */
      ,a10.f_prt_stkvaluetonav /* 持有股票市值占基金净值比例(%) */
      ,a10.f_prt_enddate /* 截止日期 */
  FROM ${DL_ODS_INFO_SCHEMA}.s081_pdata_chinamutualfundstockportfolio a10
 INNER JOIN ${DL_ODS_INFO_SCHEMA}.s081_pdata_chinamutualfunddescription a20
    ON a10.s_info_windcode = a20.f_info_windcode AND
       a20.f_info_setupdate IS NOT NULL AND
       a20.f_info_maturitydate IS NULL AND
       a20.f_info_isinitial = '1'
 INNER JOIN ${DL_ODS_INFO_SCHEMA}.s081_pdata_cmfbalancesheet a30 
    on a30.s_info_windcode = a10.s_info_windcode and a10.f_prt_enddate = a30.report_period
;
 
DROP TABLE IF EXISTS t_fnd_scrt_qtr_indx_derivativeindicator; 
CREATE LOCAL TEMP TABLE t_fnd_scrt_qtr_indx_derivativeindicator ON COMMIT PRESERVE ROWS AS 
SELECT trade_dt
      ,s_info_windcode
      ,s_val_mv
      ,s_val_pe_ttm
      ,s_val_pb_new
      ,s_dq_mv
      ,s_val_pcf_ocfttm
  FROM ${DL_ODS_INFO_SCHEMA}.s081_pdata_ashareeodderivativeindicator_b08
UNION ALL
SELECT financial_trade_dt
      ,s_info_windcode
      ,s_val_mv
      ,s_val_pe_ttm
      ,s_val_pb_new
      ,s_dq_mv
      ,s_val_pcf_ocfttm
  FROM ${DL_ODS_INFO_SCHEMA}.s081_pdata_hkshareeodderivativeindex_b14;


 

INSERT /*+ direct */ INTO tmp_dws_inv_scrt_indx_n1 (
		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
)          
SELECT DATE(a1.f_prt_enddate) AS f_prt_enddate
      ,'fnd_stck_pe_901556' AS indx_id
      ,a1.main_code
      ,a1.s_info_windcode
      ,'基金持仓股票PE(加权平均法)' AS indx_nm
      ,SUM(a50.s_val_pe_ttm * a1.f_prt_stkvalue) / NULLIFZERO(SUM(a1.f_prt_stkvalue)) AS s_val_pe_ttm 
	  /*20260402 yc: f_prt_stkvaluetonav字段由于精度问题存在部分为0的值，导致计算后部分数据丢失，改用f_prt_stkvalue代替进行计算*/
      ,TO_DATE('${TX_DATE_BATCH}', 'YYYYMMDD') etl_btch_dt
      ,'cdm.dws_inv_scrt_indx_n1' etl_src_tbl_nm
      ,'${ETL_JOB}' etl_job_nm
      ,SYSDATE etl_ld_tm
  FROM t_fnd_scrt_qtr_indx_privalue a1
 INNER JOIN t_fnd_scrt_qtr_indx_derivativeindicator a50
    ON a1.s_info_stockwindcode = a50.s_info_windcode AND
       a1.f_prt_enddate = a50.trade_dt AND
       a50.s_val_pe_ttm <= 300 AND
       a50.s_val_pe_ttm >= -100
 WHERE a1.main_code IS NOT NULL
 GROUP BY DATE(a1.f_prt_enddate)
         ,a1.main_code
         ,a1.s_info_windcode;


INSERT /*+ direct */ INTO tmp_dws_inv_scrt_indx_n1 (
		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
)          
SELECT DATE(a1.f_prt_enddate) AS f_prt_enddate
      ,'fnd_stck_pb_901557' AS indx_id
      ,a1.main_code
      ,a1.s_info_windcode
      ,'基金持仓股票PB(加权平均法)' AS indx_nm
      ,SUM(a50.s_val_pb_new * a1.f_prt_stkvalue) / NULLIFZERO(SUM(a1.f_prt_stkvalue)) AS s_val_pb_new /*pe加权平均*/  
	  /*20260402 yc: f_prt_stkvaluetonav字段由于精度问题存在部分为0的值，导致计算后部分数据丢失，改用f_prt_stkvalue代替进行计算*/
      ,TO_DATE('${TX_DATE_BATCH}', 'YYYYMMDD') etl_btch_dt
      ,'cdm.dws_inv_scrt_indx_n1' etl_src_tbl_nm
      ,'${ETL_JOB}' etl_job_nm
      ,SYSDATE etl_ld_tm
  FROM t_fnd_scrt_qtr_indx_privalue a1
 INNER JOIN t_fnd_scrt_qtr_indx_derivativeindicator a50
    ON a1.s_info_stockwindcode = a50.s_info_windcode AND
       a1.f_prt_enddate = a50.trade_dt AND
	   a50.s_val_pb_new  IS NOT NULL AND
       a50.s_val_pb_new <> 0
 WHERE a1.main_code IS NOT NULL
 GROUP BY DATE(a1.f_prt_enddate)
         ,a1.main_code
         ,a1.s_info_windcode;


INSERT /*+ direct */ INTO tmp_dws_inv_scrt_indx_n1 (
		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
)          
SELECT DATE(a1.f_prt_enddate) AS f_prt_enddate
      ,'fnd_stck_mkt_vl_901558' AS indx_id
      ,a1.main_code
      ,a1.s_info_windcode
      ,'基金股票市值' AS indx_nm
      ,SUM(a50.s_val_mv * a1.f_prt_stkvalue) / NULLIFZERO(SUM(a1.f_prt_stkvalue)) AS s_val_mv /*总市值加权平均*/
	  /*20260402 yc: f_prt_stkvaluetonav字段由于精度问题存在部分为0的值，导致计算后部分数据丢失，改用f_prt_stkvalue代替进行计算*/
      ,TO_DATE('${TX_DATE_BATCH}', 'YYYYMMDD') etl_btch_dt
      ,'cdm.dws_inv_scrt_indx_n1' etl_src_tbl_nm
      ,'${ETL_JOB}' etl_job_nm
      ,SYSDATE etl_ld_tm
  FROM t_fnd_scrt_qtr_indx_privalue a1
 INNER JOIN t_fnd_scrt_qtr_indx_derivativeindicator a50
    ON a1.s_info_stockwindcode = a50.s_info_windcode AND
       a1.f_prt_enddate = a50.trade_dt
 WHERE a1.main_code IS NOT NULL
 GROUP BY DATE(a1.f_prt_enddate)
         ,a1.main_code
         ,a1.s_info_windcode;



INSERT /*+ direct */ INTO tmp_dws_inv_scrt_indx_n1 (
		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
)          
SELECT DATE(a1.f_prt_enddate) AS f_prt_enddate
      ,'fnd_stckfr_crcl_mkt_vl_901559' AS indx_id
      ,a1.main_code
      ,a1.s_info_windcode
      ,'基金股票自由流通市值' AS indx_nm
      ,SUM(a50.s_dq_mv * a1.f_prt_stkvalue) / NULLIFZERO(SUM(a1.f_prt_stkvalue)) AS s_dq_mv /*流通市值加权平均*/
	  /*20260402 yc: f_prt_stkvaluetonav字段由于精度问题存在部分为0的值，导致计算后部分数据丢失，改用f_prt_stkvalue代替进行计算*/
      ,TO_DATE('${TX_DATE_BATCH}', 'YYYYMMDD') etl_btch_dt
      ,'cdm.dws_inv_scrt_indx_n1' etl_src_tbl_nm
      ,'${ETL_JOB}' etl_job_nm
      ,SYSDATE etl_ld_tm
  FROM t_fnd_scrt_qtr_indx_privalue a1
 INNER JOIN t_fnd_scrt_qtr_indx_derivativeindicator a50
    ON a1.s_info_stockwindcode = a50.s_info_windcode AND
       a1.f_prt_enddate = a50.trade_dt
 WHERE a1.main_code IS NOT NULL
 GROUP BY DATE(a1.f_prt_enddate)
         ,a1.main_code
         ,a1.s_info_windcode;


DELETE /*+ direct */ FROM ${CDM_SCHEMA}.dws_inv_scrt_indx_n1
WHERE etl_job_nm = '${ETL_JOB}' ;


       
/*把临时表中数据插入到原表中*/
INSERT /*+direct*/
INTO ${CDM_SCHEMA}.dws_inv_scrt_indx_n1 (
		dt                                   /*日期*/
   ,indx_id                              /*指标ID*/
   ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   ,wind_cd                              /*Wind代码*/
   ,indx_nm                              /*指标名称*/
   ,indx_vl                              /*指标值*/
   ,etl_btch_dt                          /*批量日期*/
   ,etl_src_tbl_nm                       /*源表名*/
   ,etl_job_nm                           /*加工作业名*/
   ,etl_ld_tm                            /*加工时间*/
)
SELECT dt                                   /*日期*/
   	  ,indx_id                              /*指标ID*/
   	  ,scrt_srrg_key                        /*证券代理键（证券主数据系统内码）*/
   	  ,wind_cd                              /*Wind代码*/
   	  ,indx_nm                              /*指标名称*/
   	  ,indx_vl                              /*指标值*/
   	  ,etl_btch_dt                          /*批量日期*/
   	  ,etl_src_tbl_nm                       /*源表名*/
   	  ,etl_job_nm                           /*加工作业名*/
   	  ,etl_ld_tm                            /*加工时间*/
FROM tmp_dws_inv_scrt_indx_n1;
/*-ENDFOR*/
		  
		   
