from sparktk.loggers import log_load; log_load(__name__); del log_load

from sparktk.propobj import PropertiesObject
from sparktk.frame.ops.classification_metrics_value import ClassificationMetricsValue
from sparktk.lazyloader import implicit
import os

def train(frame,
          label_column,
          observation_columns,
          num_classes = 2,
          num_trees = 1,
          impurity = "gini",
          max_depth = 4,
          max_bins = 100,
          seed = None,
          categorical_features_info = None,
          feature_subset_category = None):
    """
    Creates a Random Forest Classifier Model by training on the given frame

    Parameters
    ----------

    :param frame: (Frame) frame frame of training data
    :param label_column: (str) Column name containing the label for each observation
    :param observation_columns: (list(str)) Column(s) containing the observations
    :param num_classes: (int) Number of classes for classification. Default is 2
    :param num_trees: (int) Number of tress in the random forest. Default is 1
    :param impurity: (str) Criterion used for information gain calculation. Supported values "gini" or "entropy".
                    Default is "gini"
    :param max_depth: (int) Maximum depth of the tree. Default is 4
    :param max_bins: (int) Maximum number of bins used for splitting features. Default is 100
    :param seed: (Optional(int)) Random seed for bootstrapping and choosing feature subsets. Default is a randomly chosen seed
    :param categorical_features_info: (Optional(Dict(Int -> Int)) Arity of categorical features. Entry (n-> k) indicates that feature 'n' is categorical
                                   with 'k' categories indexed from 0:{0,1,...,k-1}
    :param feature_subset_category: (Optional(str)) Number of features to consider for splits at each node.
                                 Supported values "auto","all","sqrt","log2","onethird".
                                 If "auto" is set, this is based on num_trees: if num_trees == 1, set to "all"
                                 ; if num_trees > 1, set to "sqrt"

    :return: (RandomForestClassifierModel) The trained random forest classifier model

    Notes
    -----
    Random Forest is a supervised ensemble learning algorithm which can be used to perform binary and
    multi-class classification. The Random Forest Classifier model is initialized, trained on columns of a frame,
    used to predict the labels of observations in a frame, and tests the predicted labels against the true labels.
    This model runs the MLLib implementation of Random Forest. During training, the decision trees are trained
    in parallel. During prediction, each tree's prediction is counted as vote for one class. The label is predicted
    to be the class which receives the most votes. During testing, labels of the observations are predicted and
    tested against the true labels using built-in binary and multi-class Classification Metrics.


    """
    tc = frame._tc
    _scala_obj = get_scala_obj(tc)
    seed = int(os.urandom(2).encode('hex'), 16) if seed is None else seed
    scala_model = _scala_obj.train(frame._scala,
                                   label_column,
                                   tc.jutils.convert.to_scala_list_string(observation_columns),
                                   num_classes,
                                   num_trees,
                                   impurity,
                                   max_depth,
                                   max_bins,
                                   seed,
                                   __get_categorical_features_info(tc, categorical_features_info),
                                   tc.jutils.convert.to_scala_option(feature_subset_category))

    return RandomForestClassifierModel(tc, scala_model)

def __get_categorical_features_info(tc, c):
    if c is not None:
        c = tc.jutils.convert.to_scala_map(c)
    return tc.jutils.convert.to_scala_option(c)


def load(path, tc=implicit):
    """load RandomForestClassifierModel from given path"""
    if tc is implicit:
        implicit.error("tc")
    return tc.load(path, RandomForestClassifierModel)


def get_scala_obj(tc):
    """Gets reference to the scala object"""
    return tc.sc._jvm.org.trustedanalytics.sparktk.models.classification.random_forest_classifier.RandomForestClassifierModel


class RandomForestClassifierModel(PropertiesObject):
    """
    A trained Random Forest Classifier model

    Example
    -------

        >>> frame = tc.frame.create([[1,19.8446136104,2.2985856384],[1,16.8973559126,2.6933495054],
        ...                                 [1,5.5548729596,2.7777687995],[0,46.1810010826,3.1611961917],
        ...                                 [0,44.3117586448,3.3458963222],[0,34.6334526911,3.6429838715]],
        ...                                 [('Class', int), ('Dim_1', float), ('Dim_2', float)])

        >>> frame.inspect()
        [#]  Class  Dim_1          Dim_2
        =======================================
        [0]      1  19.8446136104  2.2985856384
        [1]      1  16.8973559126  2.6933495054
        [2]      1   5.5548729596  2.7777687995
        [3]      0  46.1810010826  3.1611961917
        [4]      0  44.3117586448  3.3458963222
        [5]      0  34.6334526911  3.6429838715

        >>> model = tc.models.classification.random_forest_classifier.train(frame, 'Class', ['Dim_1', 'Dim_2'], num_classes=2, num_trees=1, impurity="entropy", max_depth=4, max_bins=100)

        >>> model.predict(frame, ['Dim_1', 'Dim_2'])

        >>> frame.inspect()
        [#]  Class  Dim_1          Dim_2         predicted_class
        ========================================================
        [0]      1  19.8446136104  2.2985856384                1
        [1]      1  16.8973559126  2.6933495054                1
        [2]      1   5.5548729596  2.7777687995                1
        [3]      0  46.1810010826  3.1611961917                0
        [4]      0  44.3117586448  3.3458963222                0
        [5]      0  34.6334526911  3.6429838715                0

        >>> test_metrics = model.test(frame, ['Dim_1','Dim_2'])

        >>> test_metrics
        accuracy         = 1.0
        confusion_matrix =             Predicted_Pos  Predicted_Neg
        Actual_Pos              3              0
        Actual_Neg              0              3
        f_measure        = 1.0
        precision        = 1.0
        recall           = 1.0

        >>> model.save("sandbox/randomforestclassifier")

        >>> restored = tc.load("sandbox/randomforestclassifier")

        >>> restored.label_column == model.label_column
        True

        >>> restored.seed == model.seed
        True

        >>> set(restored.observation_columns) == set(model.observation_columns)
        True

    """

    def __init__(self, tc, scala_model):
        self._tc = tc
        tc.jutils.validate_is_jvm_instance_of(scala_model, get_scala_obj(tc))
        self._scala = scala_model

    @staticmethod
    def _from_scala(tc, scala_model):
        """Loads a random forest classifier model from a scala model"""
        return RandomForestClassifierModel(tc, scala_model)

    @property
    def label_column(self):
        """column containing the label used for model training"""
        return self._scala.labelColumn()

    @property
    def observation_columns(self):
        """observation columns used for model training"""
        return self._tc.jutils.convert.from_scala_seq(self._scala.observationColumns())

    @property
    def num_classes(self):
        """number of classes in the trained model"""
        return self._scala.numClasses()

    @property
    def num_trees(self):
        """number of trees in the trained model"""
        return self._scala.numTrees()

    @property
    def impurity(self):
        """impurity value of the trained model"""
        return self._scala.impurity()

    @property
    def max_depth(self):
        """maximum depth of the trained model"""
        return self._scala.maxDepth()

    @property
    def max_bins(self):
        """maximum bins in the trained model"""
        return self._scala.maxBins()

    @property
    def seed(self):
        """seed used during training of the model"""
        return self._scala.seed()

    @property
    def categorical_features_info(self):
        """categorical feature dictionary used during model training"""
        s = self._tc.jutils.convert.from_scala_option(self._scala.categoricalFeaturesInfo())
        if s:
            return self._tc.jutils.convert.scala_map_to_python(s)
        return None

    @property
    def feature_subset_category(self):
        """feature subset category of the trained model"""
        return self._tc.jutils.convert.from_scala_option(self._scala.featureSubsetCategory())

    def predict(self, frame, columns=None):
        """predict the frame given the trained model"""
        c = self.__columns_to_option(columns)
        self._scala.predict(frame._scala, c)

    def test(self, frame, columns=None):
        """test the frame given the trained model"""
        c = self.__columns_to_option(columns)
        return ClassificationMetricsValue(self._tc, self._scala.test(frame._scala, c))

    def __columns_to_option(self, c):
        if c is not None:
            c = self._tc.jutils.convert.to_scala_list_string(c)
        return self._tc.jutils.convert.to_scala_option(c)

    def save(self, path):
        """save the trained model to path"""
        self._scala.save(self._tc._scala_sc, path)

del PropertiesObject
