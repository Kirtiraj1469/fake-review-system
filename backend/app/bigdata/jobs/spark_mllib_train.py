#!/usr/bin/env python3
"""Train and evaluate a real Spark MLlib logistic regression from HDFS JSONL."""
import json
import sys
from pyspark.sql import SparkSession, functions as F
from pyspark.ml import Pipeline
from pyspark.ml.feature import RegexTokenizer, StopWordsRemover, HashingTF, IDF
from pyspark.ml.classification import LogisticRegression
from pyspark.ml.evaluation import MulticlassClassificationEvaluator

def canonical_label(column):
    normalized = F.upper(F.trim(column.cast("string")))
    fake = normalized.isin("CG", "FAKE", "0", "0.0", "FALSE")
    genuine = normalized.isin("OR", "GENUINE", "REAL", "1", "1.0", "TRUE")
    return F.when(fake, F.lit(0.0)).when(genuine, F.lit(1.0)).otherwise(F.lit(None).cast("double"))

def main(input_path, output_root):
    spark = SparkSession.builder.appName("FakeReviewSparkMLlib").getOrCreate()
    spark.sparkContext.setLogLevel("WARN")
    try:
        source = spark.read.json(input_path)
        if not {"text_", "label"}.issubset(source.columns):
            raise ValueError("Input JSONL must contain text_ and label fields.")
        data = (source.select(F.trim(F.col("text_").cast("string")).alias("text"),
                              canonical_label(F.col("label")).alias("label"))
                      .where(F.col("text").isNotNull() & (F.length("text") > 0) & F.col("label").isNotNull()))
        if data.count() < 10:
            raise ValueError("At least 10 valid labeled rows are required for a stable train/test split.")
        counts = {int(row["label"]): row["count"] for row in data.groupBy("label").count().collect()}
        if 0 not in counts or 1 not in counts:
            raise ValueError("The data must include both fake (CG/0) and genuine (OR/1) labels.")
        train, test = data.randomSplit([0.8, 0.2], seed=42)
        if not train.take(1) or not test.take(1):
            raise ValueError("The deterministic split produced an empty partition.")
        tokenizer = RegexTokenizer(inputCol="text", outputCol="tokens", pattern="\\W+", minTokenLength=2)
        stop_words = StopWordsRemover(inputCol="tokens", outputCol="filtered")
        hashing = HashingTF(inputCol="filtered", outputCol="raw_features", numFeatures=1 << 16)
        idf = IDF(inputCol="raw_features", outputCol="features", minDocFreq=2)
        logistic = LogisticRegression(featuresCol="features", labelCol="label", maxIter=50, regParam=0.01, elasticNetParam=0.0)
        pipeline = Pipeline(stages=[tokenizer, stop_words, hashing, idf, logistic])
        model = pipeline.fit(train)
        predictions = model.transform(test).cache()
        evaluators = {name: MulticlassClassificationEvaluator(labelCol="label", predictionCol="prediction", metricName=metric)
                      for name, metric in [("accuracy", "accuracy"), ("precision", "weightedPrecision"),
                                           ("recall", "weightedRecall"), ("f1", "f1") ]}
        metrics = {name: float(evaluator.evaluate(predictions)) for name, evaluator in evaluators.items()}
        confusion = [{"actual": int(row["label"]), "predicted": int(row["prediction"]), "count": row["count"]}
                     for row in predictions.groupBy("label", "prediction").count().collect()]
        metrics.update({"algorithm": "Spark MLlib LogisticRegression", "seed": 42,
                        "valid_rows": int(data.count()), "train_rows": int(train.count()),
                        "test_rows": int(test.count()), "class_counts": {str(k): int(v) for k,v in counts.items()},
                        "confusion_matrix": confusion,
                        "spark_master": spark.sparkContext.master,
                        "deploy_mode": spark.sparkContext.getConf().get("spark.submit.deployMode", "unknown")})
        model_path, metrics_path = output_root.rstrip("/") + "/model", output_root.rstrip("/") + "/metrics"
        jvm = spark.sparkContext._jvm
        fs = jvm.org.apache.hadoop.fs.FileSystem.get(spark.sparkContext._jsc.hadoopConfiguration())
        for path in (model_path, metrics_path):
            hadoop_path = jvm.org.apache.hadoop.fs.Path(path)
            if fs.exists(hadoop_path):
                fs.delete(hadoop_path, True)
        model.write().overwrite().save(model_path)
        spark.sparkContext.parallelize([json.dumps(metrics, sort_keys=True)]).saveAsTextFile(metrics_path)
        print("SPARK_RUN_METRICS=" + json.dumps(metrics, sort_keys=True))
        print(f"Saved Spark MLlib model to {model_path}")
        print(f"Saved Spark metrics to {metrics_path}")
        predictions.unpersist()
    finally:
        spark.stop()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("Usage: spark_mllib_train.py HDFS_INPUT_JSONL HDFS_OUTPUT_ROOT")
    main(sys.argv[1], sys.argv[2])
