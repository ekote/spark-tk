/**
 * Copyright (c) 2016 Intel Corporation 
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *       http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package org.trustedanalytics.sparktk.models.timeseries.arimax

import com.cloudera.sparkts.models.{ ARIMAX => SparkTsArimax, ARIMAXModel => SparkTsArimaxModel }
import org.apache.commons.lang.StringUtils
import org.apache.spark.SparkContext
import org.apache.spark.mllib.linalg.DenseVector
import org.apache.spark.sql.Row
import org.json4s.JsonAST.JValue
import org.trustedanalytics.sparktk.TkContext
import breeze.linalg.{ max, DenseVector => BreezeDenseVector }
import org.trustedanalytics.sparktk.frame.internal.ops.timeseries.TimeSeriesFunctions
import org.trustedanalytics.sparktk.frame.internal.rdd.FrameRdd
import org.trustedanalytics.sparktk.frame.{ Column, DataTypes, Frame }
import org.trustedanalytics.sparktk.saveload.{ SaveLoad, TkSaveLoad, TkSaveableObject }

object ArimaxModel extends TkSaveableObject {

  /**
   * Current format version for model save/load
   */
  private val currentFormatVersion: Int = 1

  /**
   * List of format version that are valid for loading
   */
  private val validFormatVersions = List[Int](currentFormatVersion)

  /**
   * Creates Autoregressive Integrated Moving Average with Exogeneous Variables (ARIMAX) model from the specified time
   * series values.
   *
   * Given a time series, fits an non-seasonal Autoregressive Integrated Moving Average with Exogeneous Variables (ARIMAX)
   * model of order (p, d, q), where p represents the autoregression terms, d represents the order of differencing,
   * q represents the moving average error terms, xregMaxLag represents the maximum lag order for exogenous variables,
   * includeOriginalXreg is a boolean flag indicating if the non-lagged exogenous variables should be included.
   * If includeIntercept is true, the model is fitted with an intercept. Exogenous Variables are represented by xColumns.
   *
   * If the specified set of exogenous variables is not invertible, an exception is thrown stating that
   * the "matrix is singular".  This happens when there are certain patterns in the dataset or columns of all
   * zeros.  In order to work around the singular matrix issue, try selecting a different set of columns for
   * exogenous variables, or use a different time window for training.
   *
   * @param frame A frame to train the model on.
   * @param timeseriesColumn Name of the column that contains the time series values.
   * @param xColumns Names of the column(s) that contain the values of previous exogenous regressors.
   * @param p Autoregressive order
   * @param d Differencing order
   * @param q Moving average order
   * @param xregMaxLag The maximum lag order for exogenous variables.
   * @param includeOriginalXreg If true, the model is fit with an intercept for exogenous variables. Default is True.
   * @param includeIntercept If true, the model was fit with an intercept.
   * @return The trained ARIMAX model
   */
  def train(frame: Frame,
            timeseriesColumn: String,
            xColumns: Seq[String],
            p: Int,
            d: Int,
            q: Int,
            xregMaxLag: Int,
            includeOriginalXreg: Boolean = true,
            includeIntercept: Boolean = true,
            initParams: Option[Seq[Double]] = None): ArimaxModel = {

    require(frame != null, "frame is required")
    require(StringUtils.isNotEmpty(timeseriesColumn), "TimeseriesColumn must not be null nor empty")
    require(xColumns != null && xColumns.nonEmpty, "Must provide at least one x column.")

    val trainFrameRdd = new FrameRdd(frame.schema, frame.rdd)
    trainFrameRdd.cache()
    val userInitParams = if (initParams.isDefined) initParams.get.toArray else null

    val (yVector, xMatrix) = TimeSeriesFunctions.getYAndXFromFrame(trainFrameRdd, timeseriesColumn, xColumns)
    val ts = new DenseVector(yVector.toArray)

    val arimaxModel = SparkTsArimax.fitModel(p, d, q, ts, xMatrix, xregMaxLag, includeOriginalXreg, includeIntercept, userInitParams)
    trainFrameRdd.unpersist()

    ArimaxModel(timeseriesColumn, xColumns, p, d, q, xregMaxLag, includeOriginalXreg, includeIntercept, initParams, arimaxModel)
  }

  /**
   * Load a ArimaxModel from the given path
   * @param tc TkContext
   * @param path location
   * @return
   */
  def load(tc: TkContext, path: String): ArimaxModel = {
    tc.load(path).asInstanceOf[ArimaxModel]
  }

  /**
   * Load model from file
   *
   * @param sc active spark context
   * @param path the source path
   * @param formatVersion the version of the format for the tk metadata that should be recorded.
   * @param tkMetadata the data to save (should be a case class), must be serializable to JSON using json4s
   * @return ArimaxModel loaded from the specified file
   */
  override def loadTkSaveableObject(sc: SparkContext, path: String, formatVersion: Int, tkMetadata: JValue): Any = {
    validateFormatVersion(formatVersion, validFormatVersions: _*)
    val m: ArimaxModelTkMetaData = SaveLoad.extractFromJValue[ArimaxModelTkMetaData](tkMetadata)

    // Define the spark-ts ARIMAX model
    val sparkModel = new SparkTsArimaxModel(m.p, m.d, m.q, m.xregMaxLag, m.coefficients, m.includeOriginalXreg, m.includeIntercept)

    // Create ArimaxModel to return
    ArimaxModel(m.timeseriesColumn, m.xColumns, m.p, m.d, m.q, m.xregMaxLag, m.includeOriginalXreg, m.includeIntercept, m.initParams, sparkModel)
  }
}

case class ArimaxModel private[arimax] (timeseriesColumn: String,
                                        xColumns: Seq[String],
                                        p: Int,
                                        d: Int,
                                        q: Int,
                                        xregMaxLag: Int,
                                        includeOriginalXreg: Boolean = true,
                                        includeIntercept: Boolean = true,
                                        initParams: Option[Seq[Double]],
                                        arimaxModel: SparkTsArimaxModel) extends Serializable {

  /**
   * An intercept term
   */
  def c: Double = arimaxModel.coefficients(0)

  /**
   * Coefficient values: AR with increasing degrees
   */
  def ar: Seq[Double] = arimaxModel.coefficients.slice(1, p + 1)

  /**
   * Coefficient values: MA with increasing degrees
   */
  def ma: Seq[Double] = arimaxModel.coefficients.slice(p + 1, p + q + 1)

  /**
   * Coefficient values: xreg with increasing degrees
   */
  def xreg: Seq[Double] = arimaxModel.coefficients.drop(p + q + 1)

  def predict(frame: Frame,
              predictTimeseriesColumn: String,
              predictXColumns: Seq[String]): Frame = {
    require(frame != null, "Frame cannot be null.")
    require(predictXColumns.length == xColumns.length, "Number of columns for train and predict should be the same")

    // Get vector or y values and matrix of x values
    val predictFrameRdd = new FrameRdd(frame.schema, frame.rdd)
    val (yVector, xMatrix) = TimeSeriesFunctions.getYAndXFromFrame(predictFrameRdd, predictTimeseriesColumn, predictXColumns)

    // Find the maximum lag and fill that many spots with nulls, followed by the predicted y values
    val maxLag = max(arimaxModel.p, arimaxModel.q)
    val ts = new BreezeDenseVector(yVector.toArray)

    val predictions = Array.fill(maxLag) { null } ++ arimaxModel.predict(ts, xMatrix).toArray
    val numPredictions = predictions.length

    val dataWithPredictions = frame.rdd.zipWithIndex().map {
      case (row: Row, index: Long) =>
        if (numPredictions > index)
          Row.fromSeq(row.toSeq :+ predictions(index.toInt))
        else
          Row.fromSeq(row.toSeq :+ null)
    }

    val schemaWithPredictions = frame.schema.addColumn(Column("predicted_y", DataTypes.float64))

    new Frame(dataWithPredictions, schemaWithPredictions)
  }
  /**
   * Saves trained model to the specified path
   *
   * @param sc spark context
   * @param path path to save file
   */
  def save(sc: SparkContext, path: String): Unit = {
    val tkMetadata = ArimaxModelTkMetaData(timeseriesColumn, xColumns, p, d, q, xregMaxLag, includeOriginalXreg, includeIntercept, arimaxModel.coefficients, initParams)
    TkSaveLoad.saveTk(sc, path, ArimaxModel.formatId, ArimaxModel.currentFormatVersion, tkMetadata)
  }
}

/**
 * TK Metadata that will be stored as part of the ARIMAX model
 *
 * @param timeseriesColumn Name of the column that contains the time series values.
 * @param xColumns Names of the column(s) that contain the values of previous exogenous regressors.
 * @param p Autoregressive order
 * @param d Differencing order
 * @param q Moving average order
 * @param xregMaxLag The maximum lag order for exogenous variables.
 * @param includeOriginalXreg If true, the model is fit with an intercept for exogenous variables. Default is True.
 * @param includeIntercept If true, the model is fit with an intercept. Default is True.
 * @param coefficients Coefficients from the trained model
 * @param initParams User provided initial parameters for optimization.
 */
case class ArimaxModelTkMetaData(timeseriesColumn: String,
                                 xColumns: Seq[String],
                                 p: Int,
                                 d: Int,
                                 q: Int,
                                 xregMaxLag: Int,
                                 includeOriginalXreg: Boolean,
                                 includeIntercept: Boolean,
                                 coefficients: Array[Double],
                                 initParams: Option[Seq[Double]]) extends Serializable