Enrollment is expected to take the most time.  Video frames will be streamed to the service through GRPC.  The service should process those frames as quickly as possible.  At the conclusion of the enrollment any templates should be stored into a database.  

A typical enrollment may include:
- Video frames will be streamed to the service through GRPC
- Image enhancement is applied
- Face and body detection is applied
- Tracklets are updated
- Templates are extracted or updated
- Templates are stored in a database

For Phase 1 this process can take up to 5x realtime.  A typical workload would be a 1080P video file at 30 fps.  In realtime each frame should accounts for 0.0333 seconds. With the 5x adjustment processing should take no more than 0.1666 second per frame on average.  Computation times will be computed for videos of 5 seconds or longer and **on average** should meet these limits.  Shorter videos may take slightly longer due to the overhead of starting/stopping processing, variations in time needed to process each frame, etc.  For longer videos these costs are expected to be amortized into the total computation. Note that GRPC services can be threaded which means that frames can be processed concurrently while GRPC threads are handling the I/O with the client. 

Timings for verification and search results in Phase 1 are selected to meet computational speed requirements for BRIAR tests.  Requirements for Phases 2 and 3 are selected based on **minimum** operational needs.

# Batch Processing and Low Latency

The software may be used in two modes with respect to speed and latency.  By default, the software should operate in a batch processing mode where images and videos are processed in the shortest amount of time possible.  In this mode many frames could be collected into large buffers and processed simultaneously which may result in high latency.  An API option will be provide that will request a low latency mode (specifics TBD).  In this mode the software should return results with less than 2 second latency. The low latency mode should be suitable for processing live streams with real time alerts. Both modes should be capable of processing videos of undetermined length (hours or days) without significant usage of system memory or other system resources. Currently batch mode for photos is not supported by the API and these can be processed individually.

_As always creative solutions to improve speed and latency are encouraged._

| Evaluation | Batch Processing | Low Latency | Notes |
| ------ | ------ | ------ | ------ |
| Phase 1 | Yes  | Optional | Batch processing modes are expected and latency will not be evaluated. |
| Phase 2 | Yes | Yes | Less than 2 second latency modes should be implemented to support live streaming and real time alerts. |
| Phase 3 | Yes | Yes | Less than 2 second latency modes should be implemented for embedded hardware. |


# Guidance by API Call

| API Call | Phase 1 | Phase 2 & 3 | Notes | 
| --- | --- | --- | --- |
| status | < 1 second | < 1 second | This function sends back version numbers and basic service status.  It should be very fast. |
| detect | 5x realtime | 1x realtime | Same as enroll |
| track | 5x realtime | 1x realtime | Same as enroll |
| extract | 5x realtime | 1x realtime | Same as enroll |
| enroll | 5x realtime | 1x realtime | This will be the primary function used for testing. It is expected that this will take the majority of the computation time to process a video. |
| verify | < 1 second | < 1 second | The template similarity computation should be very fast. Testing will be conducted through the **database_compute_score_matrix** function so focus efforts there. |
| search | < 1 second | < 1 second | Searches should be fast and linear with respect to the size of the gallery. Testing will be conducted through the **database_compute_search_results** function so focus efforts there. |
| cluster | TBD | TBD | Not tested in Phase 1. |
| enhance | TBD | TBD | Not tested in Phase 1. |
| database_create | < 10 second | < 10 second | This is not called often so it can take more time if needed. |
| database_load | TBD | TDB | Should be linear with respect to the number of templates loaded. |
| database_retrieve | TBD | TDB | Should be linear with respect to the number of templates retrieved. |
| database_insert | < 1 second | < 1 second |  |
| database_names | < 1 second | < 1 second | Should be fast, but may be linear for large numbers of databases. |
| database_list_templates | < 1 second | < 10 second | Should be fast, but may be linear for large numbers of databases. |
| database_remove_templates | < 1 second | < 10 second | Should be fast, but may be linear for large numbers of databases. |
| database_finalize | < 1 hour | < 1 hour | Finalization is optional and may not be tested if it takes too long.  Operationally, databases may be in a constant state of change and enrollment and finalization may not be possible. |
| database_compute_score_matrix | > 4,000 comp./sec. | > 100,000 comp./sec | Should be linear with respect to the number of verifications computations in the matrix. |
| database_compute_search_results | > 4,000 comp./sec. | > 100,000 comp./sec. | Should be linear with respect to the number of search results returned.  Sublinear search algoritms are encouraged but testing may require full results. |

# Enrollment Speed Guidence

| Phase | Media Format | Compute | Subjects | Modality | Time |
| ------ | ------ | ------ | ------ | ------ | ------ | 
| 1 | 1080p@30fps (1920x1080)  | $10k | 1 | Face and Whole Body | 5x realtime |
| 1 | 4k@30fps (3840x2160)  | $10k | 1 | Face and Whole Body | 5x realtime |
| 1 | Photo (6000x4000) | $10k | 1 | Face and Whole Body | < 2 seconds |
| 2 | 1080p@30fps (1920x1080)  | $10k | 5 | Face and Whole Body | 1x realtime |
| 2 | 4k@30fps (3840x2160)  | $10k | 5 | Face and Whole Body | 1x realtime |
| 2 | Photo (6000x4000)  | $10k | 5 | Face and Whole Body | < 1 seconds |
| 3 | 1080p@30fps (1920x1080)  | embedded | 20 | Face and Whole Body | 1x realtime |
| 3 | 4k@30fps (3840x2160)  | embedded | 20 | Face and Whole Body | 1x realtime |
| 3 | Photo (6000x4000)  | embedded | 20 | Face and Whole Body | < 1 seconds |





