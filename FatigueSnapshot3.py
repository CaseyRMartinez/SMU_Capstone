# Databricks notebook source
import sys, json, requests, datetime, time, collections
from pyspark import SparkContext, SparkConf
from pyspark.sql import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
from functools import reduce
import pandas as pd
import numpy as np

sqlContext = SQLContext(sc)

def mountBLOB(storage_account_name, container):
  accountKey = "fs.azure.account.key.{}.blob.core.windows.net".format(storage_account_name)
  mountPoint = "/mnt/" + container
  extraConfig = {accountKey: }
  inputSource = "wasbs://{}@{}.blob.core.windows.net".format(container, storage_account_name)

  print("Mounting: {}".format(mountPoint))
  try:
    dbutils.fs.mount(
      source = inputSource,
      mount_point = str(mountPoint),
      extra_configs = extraConfig
    )
    print("=> Succeeded")
  except Exception as e:
    if "Directory already mounted" in str(e):
      print("=> Directory {} already mounted".format(mountPoint))
      pass
    else:
      raise(e)

  return 

mountBLOB('opsstoragedev','blade-inspections')
mountBLOB('opsstoragedev','envision-clean')
mountBLOB('opsstoragedev','metadata')


def connectionString(database):

  # Azure SQL Database
  server = 
  user = 
  password = 
  port = 
  jdbcOptions = "encrypt=true;trustServerCertificate=false;hostNameInCertificate=*.database.windows.net;loginTimeout=30;"

  jdbcUrl = "jdbc:sqlserver://" + server + ".database.windows.net:" + port + ";database=" + database + ";user=" + user+'@'+server + ";password=" + password +";" + jdbcOptions

  return jdbcUrl

# connectionString()

def writeSQL(df,database,table,mode):
  print('Writing to SQL...')
  df.write.format("jdbc") \
    .option("url", connectionString(database)) \
    .option("dbtable", table) \
    .mode(mode) \
    .save()
  return print('Done')
  
def filterInspections(df,site):
  try:
    print('filtering inspections')
    df = df.filter(df['Site']==site)\
           .filter(df['Severity'] > 1)\
           .filter(df['defectDistance'] > 20) # normalize this by blade length. 

    df2 = df.groupBy('Site','Date','WPP_ID','WTG_ID').agg(avg("Severity").alias('Severity')) #sum of severity

  except Exception as e:
    print(e)
    pass
  return df2

def joinMetaPre(df):
  try:
    print('joining meta pre...')
    WTG_models = spark.read.csv('dbfs:/mnt/metadata/WTG_Models.csv', inferSchema=True,header=True)
    WTG = spark.read.csv('dbfs:/mnt/metadata/WTG.csv', inferSchema=True,header=True)
    WPP = spark.read.csv('dbfs:/mnt/metadata/WPP.csv', inferSchema=True,header=True)

    # Join WTG and WTG_models
    WTG = WTG.join(WTG_models, WTG['WTG_Model_ID'] == WTG_models['WTG_Model_ID'],how='left')\
    .drop(WTG_models['WTG_Model_ID'])

    cols = ['WTG_ID', 'Rotor_Diameter_m']
    WTG = WTG.select(cols)

    df = df.join(WTG, df['WTG_ID'] == WTG['WTG_ID'],how='left')\
    .drop(WTG['WTG_ID'])
    
    # Join WPP
    cols = ['WPP_ID','Elevation_m']
    WPP = WPP.select(cols)

    df = df.join(WPP, df['WPP_ID'] == WPP['WPP_ID'],how='left')\
    .drop(WPP['WPP_ID'])
  
  except Exception as e:
    print(e)
    pass
  
  return df

# dfTur = joinMetaPre(dfTur)
# display(dfTur)

# COMMAND ----------

def addFeatures(df):
  try:
    print('adding features')
    
    if 'Rainfall' not in df.columns:
      df = df.withColumn('Rainfall',lit(0))
      
    cols = ['TimeStamp','WPP_ID','WTG_ID','TemOut','Elevation_m','WindSpeed','WindSpeed_STD','RotorSpd','GenSpd','Rotor_Diameter_m','Rainfall']
    df = df.select(cols)

    df = df.filter(col('TimeStamp').isNotNull())

    def calcAirDensity(temp,elevation):
      # https://www.engineeringtoolbox.com/air-altitude-pressure-d_462.html
      BP = 101325*(1-(0.0000225577*elevation)**(5.25588)) #Pa
      airDensity = BP/(287.05*temp)
      return airDensity

    calcAirDensity_udf = udf(calcAirDensity)
    

    df = df.withColumn("Elevation", col('Elevation_m').cast(FloatType())) 
    
    df = df.na.fill(0)
# #     df = df.filter(col('Elevation').isNotNull()) 
    df = df.withColumn('TemOutK', (col('TemOut')+273.15).cast(FloatType()))
     
    df = df.withColumn('airDensity',calcAirDensity_udf('TemOutK','Elevation').cast(FloatType()))
    
    df = df.withColumn('WindSpeedAdj',(col('WindSpeed')*((col('airDensity'))**(1/3))))
#     df = df.withColumn('WindSpeedAdj',(col('WindSpeed')*((col('airDensity')/101325)**(1/3))))
    
    df = df.withColumn('WindSpeedBin',round(col("WindSpeedAdj"),1))
    df = df.withColumn('TurbulenceTurbine',col('WindSpeed_STD')/col('WindSpeed'))

    df = df.withColumn('GenRotorRatio',col('GenSpd')/col('RotorSpd'))
    df = df.withColumn('TipSpeed',(col('RotorSpd')*np.pi*(col('Rotor_Diameter_m')/2)))
    
                       
                       
                       
    df = df.withColumn('RainWind',(col('Rainfall')+1)*col('TipSpeed')) # change this to tip speed
    
#     df = df.withColumn('BladeError1',abs(col('Blade1Position')-col('BladeAngleRef')))
#     df = df.withColumn('BladeError2',abs(col('Blade2Position')-col('BladeAngleRef')))
#     df = df.withColumn('BladeError3',abs(col('Blade3Position')-col('BladeAngleRef')))
#     df = df.withColumn('GearOilTempDiff',abs(col('TemGeaOil')-col('TemOut')))

    # Transform Wind Direction
    # tip speed
    # turbine age
    # Turbulence Met
    # Shear Met
    # rainfall + windspeed @high wind only?
    # pitch actual - reference
    # downtime fault code. Count number of faults. 

      # Icing
    # icing = (df['AirTC_3m_Avg'] < 3) & (abs(df['WS_ICEFREE_Avg'] - df['WS_Thies_80m_Avg']) > 1)
    # df['Icing'] = [1 if x == True else 0 for x in icing]

    # Turbulence
    # df['TurbulenceMet'] = df['WS_Thies_80m_Std'] / df['WS_Thies_80m_Avg']
    #   df['TurbulenceTurbine'] = df['wtc_AcWindSp_stddev'] / df['wtc_AcWindSp_mean']
    
  except Exception as e:
    print(e)
    pass

  return df
# dfTur3 = addFeatures(dfTur)
# display(dfTur3)

# COMMAND ----------



# COMMAND ----------

def aggTurbineData(dfTur, InspectRow):
  try:
#     print('Aggregating Turbine Data')
    dfTur = dfTur.filter(col('TimeStamp') < InspectRow['Date'])\
           .filter(col('WTG_ID') == InspectRow['WTG_ID'])
  #         print('filtered')
    dfAgg = dfTur.groupBy('WPP_ID','WTG_ID').agg(sum("TurbulenceTurbine").alias("TurbulenceTurbine"),\
                                                 sum("RainWind").alias("RainWind"))
#                                                  sum("GenRotorRatio").alias("GenRotorRatio"),
    
  #         print('grouped')
    dfAgg = dfAgg.withColumn('Severity',lit(InspectRow['Severity']))
    dfAgg = dfAgg.withColumn('InspectDate',lit(InspectRow['Date']).cast(DateType()))


  except Exception as e:
    print(e)
    pass
  return dfAgg

# for row in dfInspect2.collect():
#   testRow = row
#   break
# print(testRow)

# dfAgg = aggTurbineData(dfTur3, testRow)
# display(dfAgg)

# COMMAND ----------

# display(dfAgg)

# COMMAND ----------

def joinMetaPost(df):
  try:
  #   print('joining post')
  #   path = 'dbfs:/mnt/metadata/turbineMeta.csv'
    path = 'dbfs:/mnt/metadata/WTG.csv'
    WTG = spark.read.csv(path, inferSchema=True,header=True)
    cols = ['WTG_ID', 'OEM_ID','WTG_Model_ID','COD_Date']
    WTG = WTG.select(cols)

    df = df.join(WTG, df.WTG_ID == WTG.WTG_ID,how='left')\
              .drop(WTG['WTG_ID'])

    df = df.withColumn("OEM_ID", col('OEM_ID').cast(IntegerType()))  
    df = df.withColumn("WTG_Model_ID", col('WTG_Model_ID').cast(IntegerType()))
    # turbine Age
    df = df.withColumn("COD_Date", col('COD_Date').cast(DateType()))  
    df = df.withColumn('TurbineAge',datediff(col('InspectDate'),col('COD_Date')))
  
  except Exception as e:
    print(e)
    pass
  return df
# 
# dfAgg2 = joinMetaPost(dfAgg)

# COMMAND ----------

# display(dfAgg2)

# COMMAND ----------

def collectSiteData(dfInspect,dfTur,site):
  try:
    print(site)
    dfListRow = list()
    dfResultsSite = pd.DataFrame()
    siteRowList = filterInspections(dfInspect,site).collect()
    print('Number of Turbines:',len(siteRowList))
    counter = 0
    for row2 in siteRowList:
      dfAgg = aggTurbineData(dfTur, row2)
      rowCount = dfAgg.count()
      if rowCount > 0:
        dfAgg = joinMetaPost(dfAgg)
        dfListRow.append(dfAgg.toPandas())
        print('dfListRow:',len(dfListRow))
        counter += 1
      else:
        print('No rows')
        break
      if False: #counter == 2:
        break
    
    dfResultsSite = pd.concat(dfListRow)
        
  except Exception as e:
      print('collectSiteError')
      print(e)
      
  
  return dfResultsSite
    

# x = collectSiteData(dfInspect,dfTur3,'K2W')

# COMMAND ----------

def main():
  dfListFleet = list()
  dfResultsFleet = pd.DataFrame()
  dfInspect = spark.read.parquet("dbfs:/mnt/blade-inspections/allInspections.parquet").cache()

  for row in dfInspect.select('Site').distinct().collect():
#   for site in ['LCW','SVW','PGW','ARW','PH1','OEW','PRW','PH2']:
    try:
      site = row[0]
      dfTur = spark.read.parquet("dbfs:/mnt/envision-clean/clean_meta_sub/{}_tenAvg.parquet".format(site)).cache()
#       dfTur = spark.read.parquet("dbfs:/mnt/envision-clean/clean_turbine/{}_tenAvg.parquet".format(site)).cache().sample(False, 0.1)
#       dfTur = filterTurbineData(dfTur)
      dfTur = joinMetaPre(dfTur)
      dfTur = addFeatures(dfTur)
      dfResultsSite = collectSiteData(dfInspect,dfTur,site)

      dfListFleet.append(dfResultsSite)
      dfResultsSite.to_csv("/dbfs/mnt/blade-inspections/snapshot/snapshot{}.csv".format(site), index=False)
      print('File Saved!')
    except Exception as e:
      print(e)
      pass
  
  if len(dfListFleet) > 0:
    dfResultsFleet = pd.concat(dfListFleet)       
    print('FleetList:',site,len(dfListFleet))
    
    dfResultsFleet.to_csv("/dbfs/mnt/blade-inspections/snapshot/snapshot_all.csv", index=False)
    print('File Saved!')
#     writeSQL(dfResultsFleet,'snapshot_all')

    print('DONE')
    return dfResultsFleet
  else:
    return print('dfListFleet is empty')
  
x = main()
print(x)

# COMMAND ----------


