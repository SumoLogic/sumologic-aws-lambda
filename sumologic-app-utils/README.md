# sumologic-app-utils

This lambda function is used for creating custom resources. This application is used in conjunction with other SAM applications like sumologic-guardduty-benchmark to automate creation/deletion of Sumo Logic resources.

Made with ❤️ by Sumo Logic. Available on the [AWS Serverless Application Repository](https://aws.amazon.com/serverless)



## Setup

1. Deploying the SAM Application
    1. Go to https://serverlessrepo.aws.amazon.com/applications.
    2. Search for sumologic-app-utils.
    3. Click on the sumologic-app-utils application, and then click Deploy.
    4. Click Deploy.

## Sumo Logic API Endpoints

The `sumologic.py` client uses the following Sumo Logic REST API endpoints (base: `https://api.<deployment>.sumologic.com/api/v1` unless noted):

### Collectors & Sources
| Method | Endpoint |
|:--|:--|
| GET | `/collectors` |
| GET | `/collectors/{id}` |
| POST | `/collectors` |
| PUT | `/collectors/{id}` |
| DELETE | `/collectors/{id}` |
| GET | `/collectors/{id}/sources` |
| GET | `/collectors/{id}/sources/{source_id}` |
| POST | `/collectors/{id}/sources` |
| PUT | `/collectors/{id}/sources/{source_id}` |
| DELETE | `/collectors/{id}/sources/{source_id}` |

### Search
| Method | Endpoint |
|:--|:--|
| GET | `/logs/search` |
| POST | `/search/jobs` |
| GET | `/search/jobs/{id}` |
| GET | `/search/jobs/{id}/messages` |
| GET | `/search/jobs/{id}/records` |
| DELETE | `/search/jobs/{id}` |

### Connections
| Method | Endpoint |
|:--|:--|
| GET | `/connections/{id}` |
| POST | `/connections` |
| PUT | `/connections/{id}` |
| DELETE | `/connections/{id}?type=...` |

### Content / Folders (v2)
| Method | Endpoint |
|:--|:--|
| DELETE | `/content/{id}/delete` |
| POST | `/content/folders` |
| GET | `/content/folders/personal` |
| GET | `/content/folders/{id}` |
| PUT | `/content/folders/{id}` |
| POST | `/content/{id}/copy?destinationFolder={id}` |
| POST | `/content/folders/{id}/import?overwrite=...` |
| GET | `/content/folders/{id}/import/{job_id}/status` |
| GET | `/content/{id}/copy/{job_id}/status` |

### Apps (v1/v2)
| Method | Endpoint |
|:--|:--|
| GET | `/apps` |
| GET | `/apps/instances` (v2) |
| POST | `/apps/{id}/install` |
| GET | `/apps/install/{job_id}/status` |
| POST | `/apps/{id}/upgrade` (v2) |
| GET | `/apps/upgrade/{job_id}/status` (v2) |
| POST | `/apps/{id}/uninstall` (v2) |
| GET | `/apps/uninstall/{job_id}/status` (v2) |

### Metrics & Metric Rules
| Method | Endpoint |
|:--|:--|
| POST | `/metrics/results` |
| POST | `/metricsRules` |
| DELETE | `/metricsRules/{name}` |

### Field Extraction Rules
| Method | Endpoint |
|:--|:--|
| GET | `/extractionRules` |
| GET | `/extractionRules/{id}` |
| POST | `/extractionRules` |
| PUT | `/extractionRules/{id}` |
| DELETE | `/extractionRules/{name}` |

### Fields
| Method | Endpoint |
|:--|:--|
| GET | `/fields` |
| GET | `/fields/{id}` |
| POST | `/fields` |
| DELETE | `/fields/{id}` |

### Monitors
| Method | Endpoint |
|:--|:--|
| GET | `/monitors/root` |
| GET | `/monitors/{folder_id}/export` |
| POST | `/monitors/{folder_id}/import` |
| PUT | `/monitors/permissions/set` |
| DELETE | `/monitors/{folder_id}` |

### Dashboards
| Method | Endpoint |
|:--|:--|
| GET | `/dashboards` |
| GET | `/dashboards/{id}` |
| GET | `/dashboards/{id}/data` |

### Entity Hierarchies (v1)
| Method | Endpoint |
|:--|:--|
| GET | `/entities/hierarchies` |
| POST | `/entities/hierarchies` |
| PUT | `/entities/hierarchies/{id}` |
| DELETE | `/entities/hierarchies/{id}` |

## License

Apache License 2.0 (Apache-2.0)

## Support
Requests & issues should be filed on GitHub: https://github.com/SumoLogic/sumologic-aws-lambda/issues

