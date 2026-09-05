import unittest
import warnings
from unittest.mock import patch

from sklearn.exceptions import InconsistentVersionWarning
from ai_api.app.domains.diagnosis.model_adapter import load_model_bundle, predict
from contracts.ai_internal.case_snapshot import CaseSnapshotAiInput
from contracts.ai_internal.mvp_workflow import TargetField


class MlRuntimeTest(unittest.TestCase):
    def tearDown(self):
        load_model_bundle.cache_clear()

    def test_wrong_version_is_rejected_before_loading_model(self):
        load_model_bundle.cache_clear()
        with patch("ai_api.app.domains.diagnosis.model_adapter.sklearn.__version__", "1.9.0"), patch(
            "ai_api.app.domains.diagnosis.model_adapter.joblib.load"
        ) as loader:
            with self.assertRaisesRegex(RuntimeError, "1.6.1"):
                load_model_bundle()
            loader.assert_not_called()

    def test_real_artifact_predicts_without_version_warning(self):
        load_model_bundle.cache_clear()
        with warnings.catch_warnings():
            warnings.simplefilter("error", InconsistentVersionWarning)
            result = predict({})
        self.assertEqual(result["label"], "NORMAL")


class AutomaticQuestionContractTest(unittest.TestCase):
    def test_remote_app_question_survives_snapshot_and_is_excluded_from_recommendation(self):
        snapshot = CaseSnapshotAiInput.model_validate({
            "question_context": {"pending_question_fields": ["remote_control_app"]},
        })
        self.assertIn(TargetField.REMOTE_CONTROL_APP, snapshot.question_context.excluded_target_fields())
