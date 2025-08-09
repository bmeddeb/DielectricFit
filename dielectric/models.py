import uuid
from django.conf import settings
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone


class InputSchema(models.TextChoices):
    DK_DF = "dk_df", "Dk/Df"
    EPS = "eps", "Epsilon (ε′, ε″)"


class Transform(models.TextChoices):
    LINEAR = "linear", "Linear"
    LOG = "log", "Log"


class LossFunction(models.TextChoices):
    LINEAR = "linear", "Linear"
    HUBER = "huber", "Huber"
    SOFT_L1 = "soft_l1", "Soft L1"
    CAUCHY = "cauchy", "Cauchy"
    ARCTAN = "arctan", "Arctan"


class ArtifactKind(models.TextChoices):
    NPZ = "npz", "NumPy .npz"
    JSON = "json", "JSON"
    PARQUET = "parquet", "Parquet"
    PNG = "png", "PNG"
    PDF = "pdf", "PDF"
    CSV = "csv", "CSV"


class Dataset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        'people.Project', on_delete=models.CASCADE, related_name="datasets", null=True, blank=True
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="owned_datasets"
    )
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    input_schema = models.CharField(
        max_length=16, choices=InputSchema.choices, default=InputSchema.DK_DF
    )
    input_freq_unit = models.CharField(max_length=16, default="GHz")
    ingest_fingerprint = models.CharField(max_length=64, blank=True, null=True)
    row_count = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=32, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["project", "created_at"], name="idx_dataset_project_created"),
            models.Index(fields=["owner", "created_at"], name="idx_dataset_owner_created"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["project", "ingest_fingerprint"],
                name="uq_dataset_project_fingerprint"
            )
        ]

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Update project metadata when dataset changes
        if self.project_id:
            self.project.update_metadata()
            self.project.update_activity()


class RawDataPoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="raw_points")
    point_index = models.IntegerField(null=True, blank=True)
    frequency_hz = models.FloatField()
    dk = models.FloatField(null=True, blank=True)
    df = models.FloatField(null=True, blank=True)
    epsilon_real = models.FloatField(null=True, blank=True)
    epsilon_imag = models.FloatField(null=True, blank=True)
    tan_delta = models.FloatField(null=True, blank=True)

    def clean(self):
        """Enforce that exactly one data representation is present."""
        has_dk_df = self.dk is not None and self.df is not None
        has_epsilon = self.epsilon_real is not None and self.epsilon_imag is not None

        if not (has_dk_df ^ has_epsilon):
            raise ValidationError("Exactly one of dk/df or epsilon_real/epsilon_imag must be provided.")

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["dataset", "frequency_hz"],
                name="uq_raw_dataset_freq",
            ),
        ]
        indexes = [
            models.Index(fields=["dataset", "frequency_hz"], name="idx_raw_dataset_freq"),
        ]


class PreprocessingConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="preprocessing_configs")
    config_json = models.JSONField(default=dict)
    config_hash = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class PreprocessedDataPoint(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preprocessing_config = models.ForeignKey(
        PreprocessingConfig, on_delete=models.CASCADE, related_name="points"
    )
    frequency_hz = models.FloatField()
    epsilon_real = models.FloatField(null=True, blank=True)
    epsilon_imag = models.FloatField(null=True, blank=True)
    dk = models.FloatField(null=True, blank=True)
    tan_delta = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["preprocessing_config", "frequency_hz"],
                name="idx_preproc_freq",
            ),
        ]


class Analysis(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    preprocessing_config = models.ForeignKey(
        PreprocessingConfig, on_delete=models.CASCADE, related_name="analyses"
    )
    kk_metrics = models.JSONField(default=dict)
    features = models.JSONField(default=dict)
    scoring_breakdown = models.JSONField(default=dict)
    autosuggest_top = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ModelType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=128, unique=True)
    equation_latex = models.TextField(blank=True, default="")
    parameters_schema = models.JSONField(default=list)
    version = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} (v{self.version})"


class ModelConfig(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_type = models.ForeignKey(ModelType, on_delete=models.CASCADE, related_name="configs")
    analysis = models.ForeignKey(Analysis, on_delete=models.SET_NULL, null=True, blank=True, related_name="model_configs")
    name = models.CharField(max_length=128, blank=True, default="")
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Config for {self.model_type.name}"


class ModelParameter(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_config = models.ForeignKey(ModelConfig, on_delete=models.CASCADE, related_name="parameters")
    param_name = models.CharField(max_length=128)
    value = models.FloatField(null=True, blank=True)
    min = models.FloatField(null=True, blank=True)
    max = models.FloatField(null=True, blank=True)
    transform = models.CharField(max_length=8, choices=Transform.choices, default=Transform.LINEAR)
    tie_group = models.CharField(max_length=64, null=True, blank=True)
    scale_hint = models.FloatField(null=True, blank=True)

    def clean(self):
        """Validate the parameter against the model type's schema."""
        super().clean()
        if not self.model_config:
            return

        schema = self.model_config.model_type.parameters_schema
        if not isinstance(schema, list):
            raise ValidationError("ModelType has an invalid parameter schema.")

        valid_param_names = {p.get("name") for p in schema}
        if self.param_name not in valid_param_names:
            raise ValidationError(
                f"'{self.param_name}' is not a valid parameter for the "
                f"'{self.model_config.model_type.name}' model."
            )

    class Meta:
        indexes = [
            models.Index(fields=["model_config", "param_name"], name="idx_param_config_name")
        ]


class FittingSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    model_config = models.ForeignKey(ModelConfig, on_delete=models.CASCADE, related_name="fittings")
    preprocessing_config = models.ForeignKey(PreprocessingConfig, on_delete=models.CASCADE, related_name="fittings")
    algorithm = models.CharField(max_length=64, blank=True, default="")
    max_iter = models.IntegerField(null=True, blank=True)
    tol = models.FloatField(null=True, blank=True)
    loss_function = models.CharField(
        max_length=16, choices=LossFunction.choices, default=LossFunction.LINEAR
    )
    loss_scale = models.FloatField(default=1.0)
    freq_weighting = models.CharField(max_length=32, null=True, blank=True)
    component_weighting = models.JSONField(null=True, blank=True)
    multistart_group_id = models.UUIDField(null=True, blank=True)
    start_seed = models.IntegerField(null=True, blank=True)
    success = models.BooleanField(null=True, blank=True)
    converged_reason = models.CharField(max_length=255, blank=True, default="")
    runtime_ms = models.IntegerField(null=True, blank=True)
    rmse = models.FloatField(null=True, blank=True)
    chisq_red = models.FloatField(null=True, blank=True)
    aic = models.FloatField(null=True, blank=True)
    bic = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["multistart_group_id", "aic"], name="idx_fit_group_aic")
        ]


class ResidualDiagnostic(models.Model):
    fitting_session = models.OneToOneField(FittingSession, primary_key=True, on_delete=models.CASCADE, related_name="diagnostics")
    dw_stat = models.FloatField(null=True, blank=True)
    runs_p = models.FloatField(null=True, blank=True)
    qq_normal_p = models.FloatField(null=True, blank=True)
    autocorr_lag1 = models.FloatField(null=True, blank=True)


class FittedCurve(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fitting_session = models.ForeignKey(FittingSession, on_delete=models.CASCADE, related_name="curves")
    frequency_hz = models.FloatField()
    epsilon_real_fit = models.FloatField(null=True, blank=True)
    epsilon_imag_fit = models.FloatField(null=True, blank=True)
    dk_fit = models.FloatField(null=True, blank=True)
    tan_delta_fit = models.FloatField(null=True, blank=True)
    residual_real = models.FloatField(null=True, blank=True)
    residual_imag = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["fitting_session", "frequency_hz"], name="idx_curve_fit_freq")
        ]


class Artifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    fitting_session = models.ForeignKey(FittingSession, on_delete=models.CASCADE, related_name="artifacts")
    kind = models.CharField(max_length=16, choices=ArtifactKind.choices)
    path = models.TextField()
    sha256 = models.CharField(max_length=64, blank=True, default="")
    bytes = models.BigIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class Share(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    analysis = models.ForeignKey(Analysis, null=True, blank=True, on_delete=models.CASCADE, related_name="shares")
    fitting_session = models.ForeignKey(FittingSession, null=True, blank=True, on_delete=models.CASCADE, related_name="shares")
    token = models.CharField(max_length=64, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    can_download = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        """Ensure exactly one foreign key is set."""
        super().clean()
        if not (self.analysis_id is None) ^ (self.fitting_session_id is None):
            raise ValidationError("A Share must be linked to exactly one of an Analysis or a FittingSession.")