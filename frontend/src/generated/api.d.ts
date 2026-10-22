// Generated from FastAPI OpenAPI. Run pnpm api:generate; do not edit.
export interface paths {
  '/api/v1/datasets': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Datasets */
    get: operations['datasets_api_v1_datasets_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/datasets/{dataset_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Dataset */
    get: operations['dataset_api_v1_datasets__dataset_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/experiments': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Experiments */
    get: operations['experiments_api_v1_experiments_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/experiments/predict': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Submit Predict */
    post: operations['submit_predict_api_v1_experiments_predict_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/experiments/{identifier}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Experiment */
    get: operations['experiment_api_v1_experiments__identifier__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/health': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Health */
    get: operations['health_api_v1_health_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/jobs/{identifier}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Job */
    get: operations['job_api_v1_jobs__identifier__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/jobs/{identifier}/cancel': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    get?: never;
    put?: never;
    /** Cancel */
    post: operations['cancel_api_v1_jobs__identifier__cancel_post'];
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/jobs/{identifier}/frames/{lead}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Prediction Image */
    get: operations['prediction_image_api_v1_jobs__identifier__frames__lead__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/jobs/{identifier}/result': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Result */
    get: operations['result_api_v1_jobs__identifier__result_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/models': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Models */
    get: operations['models_api_v1_models_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/research': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Research */
    get: operations['research_api_v1_research_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/research/figures/{name}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Research Figure */
    get: operations['research_figure_api_v1_research_figures__name__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/sequences': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Sequences */
    get: operations['sequences_api_v1_sequences_get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/sequences/{sequence_id}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Sequence */
    get: operations['sequence_api_v1_sequences__sequence_id__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
  '/api/v1/sequences/{sequence_id}/frames/{frame_index}': {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    /** Frame */
    get: operations['frame_api_v1_sequences__sequence_id__frames__frame_index__get'];
    put?: never;
    post?: never;
    delete?: never;
    options?: never;
    head?: never;
    patch?: never;
    trace?: never;
  };
}
export type webhooks = Record<string, never>;
export interface components {
  schemas: {
    /** DatasetEnvelope */
    DatasetEnvelope: {
      /** Annotation Type */
      annotation_type: string;
      /** Biology Domain */
      biology_domain: string;
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      /** Doi */
      doi: string | null;
      /** Frame Count */
      frame_count: number | null;
      /** Id */
      id: string;
      /** License */
      license: string | null;
      /** Local Available */
      local_available: boolean;
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /**
       * Model Status
       * @enum {string}
       */
      model_status: 'trained' | 'untrained';
      /** Name */
      name: string;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
      /** Sequence Count */
      sequence_count: number | null;
      /** Source Url */
      source_url: string;
    } & {
      [key: string]: components['schemas']['JsonValue'];
    };
    /** DatasetListEnvelope */
    DatasetListEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      /** Items */
      items: components['schemas']['DatasetRecord'][];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    /** DatasetRecord */
    DatasetRecord: {
      /** Annotation Type */
      annotation_type: string;
      /** Biology Domain */
      biology_domain: string;
      /** Doi */
      doi: string | null;
      /** Frame Count */
      frame_count: number | null;
      /** Id */
      id: string;
      /** License */
      license: string | null;
      /** Local Available */
      local_available: boolean;
      /**
       * Model Status
       * @enum {string}
       */
      model_status: 'trained' | 'untrained';
      /** Name */
      name: string;
      /** Sequence Count */
      sequence_count: number | null;
      /** Source Url */
      source_url: string;
    } & {
      [key: string]: components['schemas']['JsonValue'];
    };
    /** ErrorEnvelope */
    ErrorEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      error: components['schemas']['SafeError'];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    /** ExperimentListEnvelope */
    ExperimentListEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      /** Items */
      items: components['schemas']['PredictionJob'][];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    /** FrameImages */
    FrameImages: {
      error: components['schemas']['ImageAsset'] | null;
      prediction: components['schemas']['ImageAsset'];
      target: components['schemas']['ImageAsset'] | null;
    };
    /** FrameRecord */
    FrameRecord: {
      /** Frame Index */
      frame_index: number;
      /** Qc Valid */
      qc_valid: boolean;
      /** Timestamp Min */
      timestamp_min: number | null;
      /** Touches Border */
      touches_border: boolean;
    } & {
      [key: string]: components['schemas']['JsonValue'];
    };
    /** Grid */
    Grid: {
      /**
       * Contour Coordinates
       * @constant
       */
      contour_coordinates: 'working-grid pixel centers';
      /**
       * Height
       * @constant
       */
      height: 64;
      /**
       * Width
       * @constant
       */
      width: 64;
    };
    /** HTTPValidationError */
    HTTPValidationError: {
      /** Detail */
      detail?: components['schemas']['ValidationError'][];
    };
    /** ImageAsset */
    ImageAsset: {
      /** Sha256 */
      sha256: string;
      /** Url */
      url: string;
    };
    /** ImplementationIdentity */
    ImplementationIdentity: {
      /** Environment */
      environment: {
        [key: string]: string | null;
      };
      /** Files Sha256 */
      files_sha256: {
        [key: string]: string;
      };
      /** Git Dirty */
      git_dirty: boolean | null;
      /** Git Sha */
      git_sha: string | null;
    };
    /** InferenceEnvironment */
    InferenceEnvironment: {
      /**
       * Convolution Fp32 Precision
       * @constant
       */
      convolution_fp32_precision: 'ieee';
      /** Cpu Threads */
      cpu_threads: number;
      /** Deterministic */
      deterministic: boolean;
    };
    /** JobEnvelope */
    JobEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      job: components['schemas']['PredictionJob'];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    JsonValue: unknown;
    /** LeadMetrics */
    LeadMetrics: {
      /** Area Mae */
      area_mae: number;
      /** Dice */
      dice: number;
      /** Empty Boundary Mismatch */
      empty_boundary_mismatch: boolean;
      /** Hausdorff95 */
      hausdorff95: number;
      /** Iou */
      iou: number;
      /** Mean Boundary Distance */
      mean_boundary_distance: number;
      /** Signed Area Error */
      signed_area_error: number;
    };
    /** ModelListEnvelope */
    ModelListEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      /** Items */
      items: components['schemas']['RegisteredModel'][];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    /** PredictionFrame */
    PredictionFrame: {
      /** Contours */
      contours: number[][][];
      images: components['schemas']['FrameImages'];
      /** Lead */
      lead: number;
      metrics: components['schemas']['LeadMetrics'] | null;
      /** Region Area */
      region_area: number;
      /** Source Frame Index */
      source_frame_index: number;
      /** Target Area */
      target_area: number | null;
      /** Target Valid */
      target_valid: boolean;
    };
    /** PredictionJob */
    PredictionJob: {
      /** Cancel Requested */
      cancel_requested: boolean;
      /** Created At Utc */
      created_at_utc: string;
      error: components['schemas']['SafeError'] | null;
      /** Id */
      id: string;
      request: components['schemas']['PredictionRequest'];
      /** Result Available */
      result_available: boolean;
      /**
       * Status
       * @enum {string}
       */
      status: 'queued' | 'running' | 'succeeded' | 'failed' | 'cancelled';
      /** Updated At Utc */
      updated_at_utc: string;
    };
    /** PredictionRequest */
    PredictionRequest: {
      /**
       * Dataset Id
       * @constant
       */
      dataset_id: 'drosophila_wound_zenodo_7660424';
      /** Horizon */
      horizon: number;
      /**
       * Model Id
       * @enum {string}
       */
      model_id:
        'persistence' | 'constant_normal_speed' | 'nca' | 'nca_regularized' | 'convgru' | 'nca_h1';
      /** Observation Start */
      observation_start: number;
      /**
       * Observations
       * @enum {integer}
       */
      observations: 2 | 4 | 8;
      /** Sequence Id */
      sequence_id: string;
    };
    /** PredictionResult */
    PredictionResult: {
      /** Created At Utc */
      created_at_utc: string;
      /**
       * Dataset Id
       * @constant
       */
      dataset_id: 'drosophila_wound_zenodo_7660424';
      /**
       * Device
       * @constant
       */
      device: 'cpu';
      /** Frames */
      frames: components['schemas']['PredictionFrame'][];
      grid: components['schemas']['Grid'];
      implementation?: components['schemas']['ImplementationIdentity'] | null;
      inference_environment: components['schemas']['InferenceEnvironment'];
      /** Job Id */
      job_id: string;
      model: components['schemas']['RegisteredModel'];
      /**
       * Model Id
       * @enum {string}
       */
      model_id:
        'persistence' | 'constant_normal_speed' | 'nca' | 'nca_regularized' | 'convgru' | 'nca_h1';
      /**
       * Precision
       * @constant
       */
      precision: 'fp32';
      /**
       * Provenance
       * @constant
       */
      provenance: 'MODEL_PREDICTION';
      request: components['schemas']['PredictionRequest'];
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
      source: components['schemas']['PredictionSource'];
      /**
       * Status
       * @constant
       */
      status: 'succeeded';
      /**
       * Target Provenance
       * @constant
       */
      target_provenance: 'DERIVED_ANNOTATION';
    };
    /** PredictionSource */
    PredictionSource: {
      /** Archive Sha256 */
      archive_sha256: string;
      /** Manifest Sha256 */
      manifest_sha256: string;
      /** Npz Sha256 */
      npz_sha256: string;
      /**
       * Original Height
       * @constant
       */
      original_height: 128;
      /**
       * Original Width
       * @constant
       */
      original_width: 128;
      /**
       * Project Split
       * @enum {string}
       */
      project_split: 'train' | 'validation' | 'test';
      /** Sequence Id */
      sequence_id: string;
      /**
       * Source Id
       * @constant
       */
      source_id: 'zenodo:7660424';
    };
    /** RegisteredModel */
    RegisteredModel: {
      /** Available */
      available: boolean;
      /** Checkpoint Sha256 */
      checkpoint_sha256: string | null;
      /**
       * Id
       * @enum {string}
       */
      id:
        'persistence' | 'constant_normal_speed' | 'nca' | 'nca_regularized' | 'convgru' | 'nca_h1';
      /**
       * Kind
       * @enum {string}
       */
      kind: 'baseline' | 'trained';
      /** Label */
      label: string;
      /** Model Git Sha */
      model_git_sha?: string | null;
      /** Parameter Count */
      parameter_count?: number | null;
      /** Run Id */
      run_id?: string | null;
      /** Seed */
      seed: number | null;
      selection: components['schemas']['Selection'] | null;
      /** Trained */
      trained: boolean;
      /** Unavailable Reason */
      unavailable_reason?: string | null;
      /** Variant */
      variant:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
    };
    /** SafeError */
    SafeError: {
      /** Code */
      code: string;
      details?: components['schemas']['JsonValue'];
      /** Message */
      message: string;
      /** Trace Id */
      trace_id?: string | null;
      /** Type */
      type?: string | null;
    };
    /** Selection */
    Selection: {
      /**
       * Criterion
       * @constant
       */
      criterion: 'validation_supervised_loss';
      /** Loss */
      loss: number | null;
      /** Step */
      step: number | null;
    };
    /** SequenceEnvelope */
    SequenceEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string;
      /** Frame Count */
      frame_count: number;
      /** Frames */
      frames: components['schemas']['FrameRecord'][];
      /** Height */
      height: number;
      /** Id */
      id: string;
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Official Split */
      official_split: string | null;
      /** Project Split */
      project_split: string | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Qc Definition */
      qc_definition?: string | null;
      /** Qc Valid Count */
      qc_valid_count: number | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
      /** Width */
      width: number;
    } & {
      [key: string]: components['schemas']['JsonValue'];
    };
    /** SequenceListEnvelope */
    SequenceListEnvelope: {
      /** Created At Utc */
      created_at_utc: string;
      /** Dataset Id */
      dataset_id: string | null;
      /** Items */
      items: components['schemas']['SequenceRecord'][];
      /** Model Id */
      model_id:
        | (
            | 'persistence'
            | 'constant_normal_speed'
            | 'nca'
            | 'nca_regularized'
            | 'convgru'
            | 'nca_h1'
          )
        | null;
      /** Provenance */
      provenance:
        | ('REAL_OBSERVED' | 'HUMAN_ANNOTATION' | 'MODEL_PREDICTION' | 'SYNTHETIC' | 'IN_SILICO')
        | null;
      /** Run Id */
      run_id: string | null;
      /**
       * Schema Version
       * @constant
       */
      schema_version: '1';
    };
    /** SequenceRecord */
    SequenceRecord: {
      /** Dataset Id */
      dataset_id: string;
      /** Frame Count */
      frame_count: number;
      /** Height */
      height: number;
      /** Id */
      id: string;
      /** Official Split */
      official_split: string | null;
      /** Project Split */
      project_split: string | null;
      /** Qc Definition */
      qc_definition?: string | null;
      /** Qc Valid Count */
      qc_valid_count: number | null;
      /** Width */
      width: number;
    } & {
      [key: string]: components['schemas']['JsonValue'];
    };
    /** ValidationError */
    ValidationError: {
      /** Context */
      ctx?: Record<string, never>;
      /** Input */
      input?: unknown;
      /** Location */
      loc: (string | number)[];
      /** Message */
      msg: string;
      /** Error Type */
      type: string;
    };
  };
  responses: never;
  parameters: never;
  requestBodies: never;
  headers: never;
  pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
  datasets_api_v1_datasets_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['DatasetListEnvelope'];
        };
      };
    };
  };
  dataset_api_v1_datasets__dataset_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        dataset_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['DatasetEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  experiments_api_v1_experiments_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ExperimentListEnvelope'];
        };
      };
    };
  };
  submit_predict_api_v1_experiments_predict_post: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody: {
      content: {
        'application/json': components['schemas']['PredictionRequest'];
      };
    };
    responses: {
      /** @description Successful Response */
      202: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['JobEnvelope'];
        };
      };
      /** @description Unprocessable Entity */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
      /** @description Service Unavailable */
      503: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ErrorEnvelope'];
        };
      };
    };
  };
  experiment_api_v1_experiments__identifier__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        identifier: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['JobEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  health_api_v1_health_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': {
            [key: string]: unknown;
          };
        };
      };
    };
  };
  job_api_v1_jobs__identifier__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        identifier: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['JobEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  cancel_api_v1_jobs__identifier__cancel_post: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        identifier: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['JobEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  prediction_image_api_v1_jobs__identifier__frames__lead__get: {
    parameters: {
      query?: {
        layer?: 'prediction' | 'target' | 'error';
      };
      header?: never;
      path: {
        identifier: string;
        lead: number;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'image/png': string;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  result_api_v1_jobs__identifier__result_get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        identifier: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['PredictionResult'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  models_api_v1_models_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['ModelListEnvelope'];
        };
      };
    };
  };
  research_api_v1_research_get: {
    parameters: {
      query?: never;
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': {
            [key: string]: unknown;
          };
        };
      };
    };
  };
  research_figure_api_v1_research_figures__name__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        name: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'image/png': string;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  sequences_api_v1_sequences_get: {
    parameters: {
      query?: {
        dataset_id?: string;
      };
      header?: never;
      path?: never;
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SequenceListEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  sequence_api_v1_sequences__sequence_id__get: {
    parameters: {
      query?: never;
      header?: never;
      path: {
        sequence_id: string;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['SequenceEnvelope'];
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
  frame_api_v1_sequences__sequence_id__frames__frame_index__get: {
    parameters: {
      query?: {
        layer?: 'observed' | 'annotation' | 'overlay';
      };
      header?: never;
      path: {
        sequence_id: string;
        frame_index: number;
      };
      cookie?: never;
    };
    requestBody?: never;
    responses: {
      /** @description Successful Response */
      200: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'image/png': string;
        };
      };
      /** @description Validation Error */
      422: {
        headers: {
          [name: string]: unknown;
        };
        content: {
          'application/json': components['schemas']['HTTPValidationError'];
        };
      };
    };
  };
}
