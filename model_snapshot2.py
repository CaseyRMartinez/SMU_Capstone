# Databricks notebook source
import sys, json, requests, datetime, time, collections, os
from pyspark import SparkContext, SparkConf
from pyspark.sql import *
from pyspark.sql.functions import *
from pyspark.sql.types import *
from functools import *
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

import sklearn

print(sklearn.__version__)
from scipy.stats import uniform, randint

from future_encoders import ColumnTransformer

import xgboost as xgb
import mlflow
import mlflow.sklearn
# https://towardsdatascience.com/building-a-linear-regression-with-pyspark-and-mllib-d065c3ba246a
# https://www.timlrx.com/2018/06/19/feature-selection-using-feature-importance-score-creating-a-pyspark-estimator/
# https://www.kaggle.com/bertcarremans/xgboost-integrating-pandas-and-sklearn

sqlContext = SQLContext(sc)

def mountBLOB(storage_account_name, container):
 


def connectionString():
  

def writeSQLDW(df,table,mode):
 
def querySQLDW(query):
 
# COMMAND ----------

# df = pd.read_csv("/dbfs/mnt/blade-inspections/snapshot/snapshot_all_new.csv")
df = querySQLDW('select * from BladeInspections.snapshot').toPandas()
print('Raw:',df.shape)
print(df.isnull().sum())
df['TurbineAge'] = df['TurbineAge'].fillna(df['TurbineAge'].median())
df.head()

# COMMAND ----------

df.describe().transpose()

# COMMAND ----------

df['TurbulenceTurbineLog'] = np.log(df['TurbulenceTurbine'].values + 1)
df['RainWindLog'] = np.log(df['RainWind'].values + 1)

df.dropna(axis=0,how='any',inplace=True)

df = df[df['RainWindLog'] < 20]
print('Processed:',df.shape)

# COMMAND ----------

# Histograms
c = 'TurbulenceTurbineLog'
fig, ax = plt.subplots()
sns.distplot(df[c] , ax=ax)
ax.set(xlabel=c,  title='Distribution of '+c)
ax.axvline(x=np.median(df[c]), color='m', label='Median', linestyle='--', linewidth=2)
ax.axvline(x=np.mean(df[c]), color='b', label='Mean', linestyle='--', linewidth=2)
ax.legend()

display(fig)

# COMMAND ----------

# Histograms
c = 'RainWindLog'
fig, ax = plt.subplots()
sns.distplot(df[c] , ax=ax)
ax.set(xlabel=c,  title='Distribution of '+c)
ax.axvline(x=np.median(df[c]), color='m', label='Median', linestyle='--', linewidth=2)
ax.axvline(x=np.mean(df[c]), color='b', label='Mean', linestyle='--', linewidth=2)
ax.legend()

display(fig)

# COMMAND ----------


# scaler = preprocessing.StandardScaler()
# X_train_minmax = mm_scaler.fit_transform(X_train)
# mm_scaler.transform(X_test)

# COMMAND ----------

# class CategoricalSelector(BaseEstimator, TransformerMixin):
#     """
#     Transformer to select a single column from the data frame to perform additional transformations on
#     Use on text columns in the data
#     """
#     def __init__(self, key):
#         self.key = key

#     def fit(self, X, y=None):
#         return self

#     def transform(self, X):
#         return X[self.key]
    
# class NumericSelector(BaseEstimator, TransformerMixin):
#     """
#     Transformer to select a single column from the data frame to perform additional transformations on
#     Use on numeric columns in the data
#     """
#     def __init__(self, colList):
#         self.colList = colList

#     def fit(self, X, y=None):
#         return self

#     def transform(self, X):
#         return X[self.colList]
  
# class Selector(BaseEstimator, TransformerMixin):
#     """
#     Transformer to select a single column from the data frame to perform additional transformations on
#     Use on numeric columns in the data
#     """
#     def __init__(self, colList):
#         self.colList = colList

#     def fit(self, X, y=None):
#         return self

#     def transform(self, X):
#         return X[self.colList]

# COMMAND ----------

# # Class to select Dataframe columns based on dtype
# class TypeSelector(BaseEstimator, TransformerMixin):
#     '''
#     Returns a dataframe while keeping only the columns of the specified dtype
#     '''
#     def __init__(self, dtype):
#         self.dtype = dtype
    
#     def fit(self, X, y=None):
#         return self
    
#     def transform(self, X):
#         assert isinstance(X, pd.DataFrame)
#         return X.select_dtypes(include=[self.dtype])
      
#       # Class to convert a categorical column into numeric values
# class StringIndexer(BaseEstimator, TransformerMixin):
#     '''
#     Returns a dataframe with the categorical column values replaced with the codes
#     Replaces missing value code -1 with a positive integer which is required by OneHotEncoder
#     '''
#     def fit(self, X, y=None):
#         return self
    
#     def transform(self, X):
#         assert isinstance(X, pd.DataFrame)
#         return X.apply(lambda s: s.cat.codes.replace(
#             {-1: len(s.cat.categories)}
#         ))

# COMMAND ----------

# from sklearn.impute import MissingIndicator
# X.replace({999.0 : np.NaN}, inplace=True)
# indicator = MissingIndicator(missing_values=np.NaN)
# indicator = indicator.fit_transform(X)
# indicator = pd.DataFrame(indicator, columns=['m1', 'm3'])

# from sklearn.impute import SimpleImputer
# imp = SimpleImputer(missing_values=np.nan, strategy='mean')
# imp.fit_transform(X)

# X.fillna(X.mean(), inplace=True)

# from sklearn.preprocessing import OrdinalEncoder
# encoder = OrdinalEncoder()
# X.edu_level = encoder.fit_transform(X.edu_level.values.reshape(-1, 1))

# from sklearn.preprocessing import OneHotEncoder
# onehot = OneHotEncoder(dtype=np.int, sparse=True)
# nominals = pd.DataFrame(
#     onehot.fit_transform(X[['sex', 'blood_type']])\
#     .toarray(),
#     columns=['F', 'M', 'AB', 'B+','O+', 'O-'])
# nominals['edu_level'] = X.edu_level

# COMMAND ----------

# MAGIC %md
# MAGIC ## Pipeline

# COMMAND ----------

# test = Pipeline([
#                     ('features', FeatureUnion(n_jobs=-1, transformer_list=[
#                         ('numeric', Pipeline([
#                                             ('selector', NumericSelector(colList=numeric_features)),
#                                             ("imputer", Imputer(missing_values=np.nan, strategy="median", axis=0)),
#                                             ('standard', StandardScaler())
#                                             ])),
#                         ('categoricals', Pipeline([
#                                                   ('selector', CategoricalSelector(key=categorical_features)),
#                                                   ('onehot', OneHotEncoder(handle_unknown='ignore'))
#                                                   ]))]))])
# test.fit_transform(X_train)

# COMMAND ----------

numeric_features = ['RainWindLog','TurbineAge','TurbulenceTurbineLog']
categorical_features = ['WTG_Model_ID']

numeric_transformer = Pipeline([
                              ("imputer", Imputer(missing_values=np.nan, strategy="median", axis=0)),
                              ('standard', StandardScaler())
                              ])

categorical_transformer = Pipeline([
                                  ('onehot', OneHotEncoder(handle_unknown='ignore'))
                                  ])

preprocessor = ColumnTransformer(
                                transformers=[
                                              ('num', numeric_transformer, numeric_features),
                                              ('cat', categorical_transformer, categorical_features)])

regressor = xgb.XGBRegressor(objective="reg:squarederror", 
                             booster="gbtree",
                             nthread=4,
                             n_jobs=-1)

clf = Pipeline(steps=[('preprocessor', preprocessor),
                      ('classifier', regressor)])

param_grid = {
              'clf__max_depth': np.arange(3, 10, 1)
             }

model = RandomizedSearchCV(param_distributions=param_grid, 
                          estimator=pipeline, 
                          n_iter=2, 
                          scoring="neg_mean_squared_error", 
                          verbose=1, 
                          cv=3)

keepcols = ['TurbulenceTurbineLog',  'RainWindLog', 'WTG_Model_ID', 'TurbineAge']
X = df[keepcols]
y = df["Severity"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Fit the estimator
model.fit(X_train, y_train)
print(model.best_score_)
print(model.best_estimator_)

preds_test = model.best_estimator_.predict(X_test)
print(mean_squared_error(y_test.values, preds_test))

# COMMAND ----------

# https://scikit-learn.org/stable/auto_examples/compose/plot_column_transformer_mixed_types.html
numeric_features = ['RainWindLog','TurbineAge','TurbulenceTurbineLog']
categorical_features = ['WTG_Model_ID']

pipeline = Pipeline([
                    ('features', FeatureUnion(n_jobs=-1, transformer_list=[
                        ('numeric', Pipeline([
                                            ('selector', NumericSelector(colList=numeric_features)),
                                            ("imputer", Imputer(missing_values=np.nan, strategy="median", axis=0)),
                                            ('standard', StandardScaler())
                                            ])),
                        ('categoricals', Pipeline([
                                                  ('selector', CategoricalSelector(key=categorical_features)),
                                                  ('onehot', OneHotEncoder(handle_unknown='ignore'))
                                                  ]))
                    ])),  # features close
                    ("clf", xgb.XGBRegressor(objective="reg:squarederror", booster="gbtree", nthread=4,n_jobs=-1))
                ])  # pipeline close

# 'clf__learning_rate': np.arange(0.05, 1.0, 0.05),
# 'clf__n_estimators': np.arange(50, 200, 50)
param_grid = {
    'clf__max_depth': np.arange(3, 10, 1)
}

# model = RandomizedSearchCV(param_distributions=param_grid, 
#                                     estimator=xgb.XGBRegressor(objective="reg:squarederror", booster="gbtree", nthread=4,n_jobs=-1), 
#                                     n_iter=2, 
#                                     scoring="neg_mean_squared_error", 
#                                     verbose=1, 
#                                     cv=3)

model = RandomizedSearchCV(param_distributions=param_grid, 
                                    estimator=pipeline, 
                                    n_iter=2, 
                                    scoring="neg_mean_squared_error", 
                                    verbose=1, 
                                    cv=3)

keepcols = ['TurbulenceTurbineLog',  'RainWindLog', 'WTG_Model_ID', 'TurbineAge']
X = df[keepcols]
y = df["Severity"]

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)

# Fit the estimator
model.fit(X_train, y_train)
print(model.best_score_)
print(model.best_estimator_)

preds_test = model.best_estimator_.predict(X_test)
print(mean_squared_error(y_test.values, preds_test))

# COMMAND ----------

# MAGIC %md
# MAGIC 
# MAGIC ## feature_importances

# COMMAND ----------

feature_importances = pd.DataFrame(model.best_estimator_.feature_importances_, columns=['importance'])
feature_importances['Feature'] = keepcols
feature_importances = feature_importances[['Feature','importance']].sort_values('importance', ascending=False)
writeSQLDW(spark.createDataFrame(feature_importances),'BladeInspections.model-feature-importances','overwrite')

# COMMAND ----------



# preds_test
# X_submit['trip_duration'] = np.exp(preds_submit) - 1
# X_submit[['id', 'trip_duration']].to_csv('bc_xgb_submission.csv', index=False)

# COMMAND ----------

p = randomized_mse2.best_estimator_.predict(X)
df['Prediction'] = p

# Now we can constuct a vector of errors
err = np.abs(p-y)
residual = p-y
df['Residual'] = residual
# Let's see the error on the first 10 predictions
# err[:10]
df.head()

createDataFrame(pandas_df)

# COMMAND ----------

# Dot product of error vector with itself gives us the sum of squared errors
total_error = np.dot(err,err)
# Compute RMSE
rmse_train = np.sqrt(total_error/len(p))
rmse_train

# COMMAND ----------

# df.to_csv("/dbfs/mnt/blade-inspections/snapshot/snapshot_pred2.csv",index=False)

writeSQLDW(spark.createDataFrame(df),'BladeInspections.snapshotPREDICT','overwrite')

# COMMAND ----------


