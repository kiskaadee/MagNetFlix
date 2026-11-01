# Protocol Documentation
<a name="top"></a>

## Table of Contents

- [magnetflix/v1/pipeline.proto](#magnetflix_v1_pipeline-proto)
    - [GetJobRequest](#magnetflix-v1-GetJobRequest)
    - [GetJobResponse](#magnetflix-v1-GetJobResponse)
    - [JobStatus](#magnetflix-v1-JobStatus)
    - [ListJobsRequest](#magnetflix-v1-ListJobsRequest)
    - [ListJobsResponse](#magnetflix-v1-ListJobsResponse)
    - [StreamJobStatusRequest](#magnetflix-v1-StreamJobStatusRequest)
    - [StreamJobStatusResponse](#magnetflix-v1-StreamJobStatusResponse)
    - [SubmitDownloadRequest](#magnetflix-v1-SubmitDownloadRequest)
    - [SubmitDownloadResponse](#magnetflix-v1-SubmitDownloadResponse)
  
    - [JobState](#magnetflix-v1-JobState)
  
    - [PipelineService](#magnetflix-v1-PipelineService)
  
- [Scalar Value Types](#scalar-value-types)



<a name="magnetflix_v1_pipeline-proto"></a>
<p align="right"><a href="#top">Top</a></p>

## magnetflix/v1/pipeline.proto



<a name="magnetflix-v1-GetJobRequest"></a>

### GetJobRequest
Request to fetch a specific job by ID.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job_id | [string](#string) |  | Unique job identifier. |






<a name="magnetflix-v1-GetJobResponse"></a>

### GetJobResponse
Response containing the status of the requested job.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job | [JobStatus](#magnetflix-v1-JobStatus) |  | The retrieved job details. |






<a name="magnetflix-v1-JobStatus"></a>

### JobStatus
Full status information for a download job.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job_id | [string](#string) |  | Unique job ID. |
| imdb_id | [string](#string) |  | IMDb ID. |
| title | [string](#string) |  | Resolved movie title from TMDB (if available). |
| year | [int32](#int32) |  | Resolved release year from TMDB (if available). |
| requested_by | [string](#string) |  | User who requested the download. |
| state | [JobState](#magnetflix-v1-JobState) |  | Current state in the pipeline. |
| progress_pct | [float](#float) |  | Download progress percentage (0.0 to 100.0). |
| download_rate_bytes | [int64](#int64) |  | Download speed in bytes per second. |
| error_message | [string](#string) |  | Detailed error message if the job failed. |
| created_at | [google.protobuf.Timestamp](#google-protobuf-Timestamp) |  | Timestamp when the job was enqueued. |
| updated_at | [google.protobuf.Timestamp](#google-protobuf-Timestamp) |  | Timestamp when the job status or progress was last updated. |
| completed_at | [google.protobuf.Timestamp](#google-protobuf-Timestamp) |  | Timestamp when terminal processing finished (COMPLETED or FAILED). |






<a name="magnetflix-v1-ListJobsRequest"></a>

### ListJobsRequest
Request to list jobs with pagination and state filtering.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| page_size | [int32](#int32) |  | Maximum number of jobs to return per page (default: 20, max: 100). |
| page_token | [string](#string) |  | Page token received from a previous ListJobsResponse next_page_token. |
| state_filter | [JobState](#magnetflix-v1-JobState) |  | Optional filter by job state. |






<a name="magnetflix-v1-ListJobsResponse"></a>

### ListJobsResponse
Paginated response containing a list of download jobs.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| jobs | [JobStatus](#magnetflix-v1-JobStatus) | repeated | List of matching jobs for the current page. |
| next_page_token | [string](#string) |  | Token to retrieve the next page of results, or empty if no more results. |






<a name="magnetflix-v1-StreamJobStatusRequest"></a>

### StreamJobStatusRequest
Request to stream job updates.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job_id | [string](#string) |  | Optional job ID to filter updates for a single job; if empty, streams all active jobs. |






<a name="magnetflix-v1-StreamJobStatusResponse"></a>

### StreamJobStatusResponse
Real-time job status event stream frame.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job | [JobStatus](#magnetflix-v1-JobStatus) |  | Current job status update. |






<a name="magnetflix-v1-SubmitDownloadRequest"></a>

### SubmitDownloadRequest
Request to submit a new movie download.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| magnet_uri | [string](#string) |  | Magnet URI of the torrent to fetch. |
| imdb_id | [string](#string) |  | IMDb ID of the movie (e.g., &#34;tt1375666&#34;). |
| requested_by | [string](#string) |  | Username of the user requesting the download (from Authelia Remote-User). |






<a name="magnetflix-v1-SubmitDownloadResponse"></a>

### SubmitDownloadResponse
Response acknowledging the job submission.


| Field | Type | Label | Description |
| ----- | ---- | ----- | ----------- |
| job_id | [string](#string) |  | Unique identifier for the created job. |
| message | [string](#string) |  | Human-readable message. |





 


<a name="magnetflix-v1-JobState"></a>

### JobState
State enumeration of a download job lifecycle.

| Name | Number | Description |
| ---- | ------ | ----------- |
| JOB_STATE_UNSPECIFIED | 0 |  |
| JOB_STATE_QUEUED | 1 |  |
| JOB_STATE_DOWNLOADING | 2 |  |
| JOB_STATE_SCANNING | 3 |  |
| JOB_STATE_VERIFYING_METADATA | 4 |  |
| JOB_STATE_ORGANIZING | 5 |  |
| JOB_STATE_COMPLETED | 6 |  |
| JOB_STATE_FAILED | 7 |  |


 

 


<a name="magnetflix-v1-PipelineService"></a>

### PipelineService
PipelineService coordinates movie download jobs, safety scans, and library relocation.

| Method Name | Request Type | Response Type | Description |
| ----------- | ------------ | ------------- | ------------|
| SubmitDownload | [SubmitDownloadRequest](#magnetflix-v1-SubmitDownloadRequest) | [SubmitDownloadResponse](#magnetflix-v1-SubmitDownloadResponse) | SubmitDownload enqueues a new movie download job. Rejects duplicate submissions if an active job for the same IMDb ID exists or if already in library. |
| GetJob | [GetJobRequest](#magnetflix-v1-GetJobRequest) | [GetJobResponse](#magnetflix-v1-GetJobResponse) | GetJob retrieves the current status and metadata of a specific job. |
| StreamJobStatus | [StreamJobStatusRequest](#magnetflix-v1-StreamJobStatusRequest) | [StreamJobStatusResponse](#magnetflix-v1-StreamJobStatusResponse) stream | StreamJobStatus streams real-time status updates. Semantics: Emits an immediate snapshot of matching active jobs upon connection, followed by subsequent state and progress change events. |
| ListJobs | [ListJobsRequest](#magnetflix-v1-ListJobsRequest) | [ListJobsResponse](#magnetflix-v1-ListJobsResponse) | ListJobs returns a paginated list of download jobs. |

 



## Scalar Value Types

| .proto Type | Notes | C++ | Java | Python | Go | C# | PHP | Ruby |
| ----------- | ----- | --- | ---- | ------ | -- | -- | --- | ---- |
| <a name="double" /> double |  | double | double | float | float64 | double | float | Float |
| <a name="float" /> float |  | float | float | float | float32 | float | float | Float |
| <a name="int32" /> int32 | Uses variable-length encoding. Inefficient for encoding negative numbers – if your field is likely to have negative values, use sint32 instead. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="int64" /> int64 | Uses variable-length encoding. Inefficient for encoding negative numbers – if your field is likely to have negative values, use sint64 instead. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="uint32" /> uint32 | Uses variable-length encoding. | uint32 | int | int/long | uint32 | uint | integer | Bignum or Fixnum (as required) |
| <a name="uint64" /> uint64 | Uses variable-length encoding. | uint64 | long | int/long | uint64 | ulong | integer/string | Bignum or Fixnum (as required) |
| <a name="sint32" /> sint32 | Uses variable-length encoding. Signed int value. These more efficiently encode negative numbers than regular int32s. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="sint64" /> sint64 | Uses variable-length encoding. Signed int value. These more efficiently encode negative numbers than regular int64s. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="fixed32" /> fixed32 | Always four bytes. More efficient than uint32 if values are often greater than 2^28. | uint32 | int | int | uint32 | uint | integer | Bignum or Fixnum (as required) |
| <a name="fixed64" /> fixed64 | Always eight bytes. More efficient than uint64 if values are often greater than 2^56. | uint64 | long | int/long | uint64 | ulong | integer/string | Bignum |
| <a name="sfixed32" /> sfixed32 | Always four bytes. | int32 | int | int | int32 | int | integer | Bignum or Fixnum (as required) |
| <a name="sfixed64" /> sfixed64 | Always eight bytes. | int64 | long | int/long | int64 | long | integer/string | Bignum |
| <a name="bool" /> bool |  | bool | boolean | boolean | bool | bool | boolean | TrueClass/FalseClass |
| <a name="string" /> string | A string must always contain UTF-8 encoded or 7-bit ASCII text. | string | String | str/unicode | string | string | string | String (UTF-8) |
| <a name="bytes" /> bytes | May contain any arbitrary sequence of bytes. | string | ByteString | str | []byte | ByteString | string | String (ASCII-8BIT) |

