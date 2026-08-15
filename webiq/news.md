# News Search v3 REST API (Beta)

> ⚠️**Beta:** News Search v3 is currently in Beta. During Beta, some queries may return fewer results than expected. Beta APIs are not ready to take dependency in production.

**Endpoint:** `POST https://api.microsoft.ai/v3/search/news`

**Sample Request:**

```bash
curl -X POST "https://api.microsoft.ai/v3/search/news" \
  -H "host: api.microsoft.ai" \
  -H "x-apikey: <Your key>" \
  -H "content-type: application/json" \
  -d '{
    "query": "latest VC funding in tech",
    "maxResults": 10,
    "language": "en",
    "region": "US",
    "maxLength": 3000
  }'
```

## Parameters

| Parameter | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| query | Yes | string | - | A search query for the news results. Maximum length is 1000 characters. |
| maxResults | No | integer | 10 | Max number of results to return. Default is 10. Maximum value is 20. |
| language | No | string | "en" | A 2-letter ISO 639-1 language code for interface language in the search results. See [Supported Languages](/documentation/supported-languages-and-regions#supported-languages) for the full list. |
| region | No | string | "US" | A 2-letter country/region code for where the results should come from (e.g. "US", "JP", "GB", etc.). See [Supported Regions](/documentation/supported-languages-and-regions#supported-regions) for the full list. |
| location | No | string | - | Location information in format "lat:\<float\>;long:\<float\>", e.g. "lat:40.753250;long:-74.003807". |
| contentFormat | No | string | "text" | The response content format. Values: "passage" (a query-dependent snippet from the full document), "text", "html", or "markdown". |
| maxLength | No | integer | 10000 | The maximum number of characters in the content field in response. Maximum value is 500000 characters. |

## Request Headers

| Field | Type | Description |
| --- | --- | --- |
| host | string | Host for Microsoft AI APIs: `api.microsoft.ai`. |
| x-apikey _or_ Authorization | string | Your API key or Entra ID access token for [authentication](/profiles). |
| content-type | string | MIME type of the request body. Use `application/json`. |

## Response

### News Response

| Field | Type | Description |
| --- | --- | --- |
| newsResults | array of newsResult | List of news article results. |
| instrumentationClickBase | string | Base URL for click ping requests. Append an `instrumentationSuffix` value from a result item to form the full ping URL. Only present for applications with the EnableInstrumentationPing profile flag. Note: User clicks can also be logged using URL redirection. When redirection is enabled, no action is required to log User clicks, and `instrumentationClickBase` will not be included in the response. See the [Instrumentation guide](/documentation/instrumentation) for setup instructions. |
| instrumentationCitationBase | string | Base URL for LLM log ping requests. Append a DATA payload to form the full ping URL. Only present for applications with the EnableInstrumentationPing profile flag. |
| traceId | string | Trace ID for debugging. |

### newsResult

| Field | Type | Description |
| --- | --- | --- |
| title | string | The title of the news. |
| url | string | The source URL of the news. |
| content | string | The detailed webpage content (aka grounding) of the news result. |
| thumbnail | thumbnail object | The thumbnail of the news article. |
| lastUpdatedAt | string | The last updated date of the news, in UTC ISO8601 format. |
| source | string | Publisher name, such as "USA TODAY \| MSN", "CNN", etc. |
| isAdult | boolean | Indicates if the content is adult. |
| clickUrl | string | Redirect URL that proxies the click through Bing. Only present when click redirect is enabled. |
| instrumentationSuffix | string | Suffix to append to the instrumentation ping URL base for this result item. Used as the K value for both the instrumentation ping URL and the `clickUrl` redirect. Present when instrumentation ping is enabled. |

> **Note:** `lastUpdatedAt` field is optional – that is, you may see empty value for this field.


### thumbnail

| Field | Type | Description |
| --- | --- | --- |
| url | string | The URL of the thumbnail. |
| width | integer | Width of the thumbnail, in pixels. |
| height | integer | Height of the thumbnail, in pixels. |

> **Note:** `thumbnail` is also an optional response object – it may not be available for certain news results.

## Error Codes

| Status Code | Error Category | Description | Common Causes |
| --- | --- | --- | --- |
| 200 | Success | The request succeeded. | - |
| 400 | Bad Request | Invalid request parameters. | Missing required fields, invalid parameter values, malformed JSON |
| 401 | Unauthorized | Authentication failed or missing. | Invalid API key, missing x-apikey header |
| 403 | Forbidden | Valid credentials but insufficient permissions. | API key lacks required permissions |
| 410 | Gone | HTTPS required. | Request made over HTTP instead of HTTPS |
| 415 | Unsupported Media Type | Content type not supported. | Missing or incorrect content-type header |
| 429 | Too Many Requests | Rate limit exceeded. | Too many requests in time window |
| 500 | Internal Server Error | Unexpected server error. | Temporary server issue |
| 503 | Service Unavailable | Service temporarily unavailable. | Maintenance or temporary outage |
| 504 | Gateway Timeout | Request timed out. | Upstream service timeout |

For detailed error handling guidance, see [Error Handling](/documentation/error-handling).

---

**See also:** [Web Search](/documentation/api-reference/web) | [Videos Search](/documentation/api-reference/videos) | [Browse](/documentation/api-reference/browse) | [Images Search (Beta)](/documentation/api-reference/images) | [Classic Search (Beta)](/documentation/api-reference/classic) | [MCP](/documentation/mcp)
