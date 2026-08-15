# Web Search v3 REST API

**Endpoint:** `POST https://api.microsoft.ai/v3/search/web`

**Sample Request:**

```bash
curl -X POST "https://api.microsoft.ai/v3/search/web" \
  -H "host: api.microsoft.ai" \
  -H "x-apikey: <Your API key>" \
  -H "content-type: application/json" \
  -d '{
    "query": "latest trends in LLM RAG",
    "maxResults": 10,
    "language": "en",
    "region": "US",
    "maxLength": 10000,
    "contentFormat": "html"
  }'
```

## Parameters

| Parameter | Required | Type | Default | Description |
| --- | --- | --- | --- | --- |
| query | Yes | string | - | A search query string. Maximum length is 1000 characters. Supports "site:" and "-site:" operators to include or exclude results from specific sites (e.g. "query site:example.com"). Use these operators only when necessary, as they inherently reduce result relevance. |
| maxResults | No | integer | 10 | Maximum number of results to return. Default is 10 and maximum value is 50. |
| language | No | string | "en" | A 2-letter ISO 639-1 language code for interface language in the search results. See [Supported Languages](/documentation/supported-languages-and-regions#supported-languages) for the full list. |
| region | No | string | "US" | A 2-letter country/region code for where the results should come from (e.g. "US", "JP", "GB", etc.). See [Supported Regions](/documentation/supported-languages-and-regions#supported-regions) for the full list. |
| location | No | string | - | Location information in format "lat:\<float\>;long:\<float\>", e.g. "lat:40.753250;long:-74.003807". If not specified, location in the query would be inferred. |
| contentFormat | No | string | "html" | The desired format of the webpage content. Values can be "passage", "text", "html", or "markdown". **passage**: query-contextual extractions — a model selects the most relevant paragraphs from the document based on the query, returned in plain text up to `maxLength`. **text**: full semantic document in plain text. **html**: full semantic document in HTML. **markdown**: full semantic document in markdown. Note: the web API does not return a `snippet` field. Use `contentFormat=passage` for query-dependent extracted content. |
| maxLength | No | integer | 10000 | The maximum number of characters in the content or passage field in response. Maximum value is 500000 characters. |

## Request Headers

| Field | Type | Description |
| --- | --- | --- |
| host | string | Host for Microsoft AI APIs: `api.microsoft.ai`. |
| x-apikey _or_ Authorization | string | Your API key or Entra ID access token for [authentication](/profiles). |
| content-type | string | MIME type of the request body. Use `application/json`. |

## Response

### Web Response

| Field | Type | Description |
| --- | --- | --- |
| webResults | array of webResult | List of web page results. |
| instrumentationClickBase | string | Base URL for click ping requests. Append an `instrumentationSuffix` value from a result item to form the full ping URL. Only present for applications with the EnableInstrumentationPing profile flag. Note: User clicks can also be logged using URL redirection. When redirection is enabled, no action is required to log User clicks, and `instrumentationClickBase` will not be included in the response. See the [Instrumentation guide](/documentation/instrumentation) for setup instructions. |
| instrumentationCitationBase | string | Base URL for LLM log ping requests. Append a DATA payload to form the full ping URL. Only present for applications with the EnableInstrumentationPing profile flag. |
| traceId | string | Trace ID for debugging. |

### webResult

| Field | Type | Description |
| --- | --- | --- |
| title | string | The title of the webpage. |
| url | string | The source URL of the webpage. |
| content | string | The detailed content (aka grounding) of the webpage. |
| crawledAt | string | The last crawled date of the webpage, follows ISO8601 format. |
| lastUpdatedAt | string | The last updated date of the webpage, follows ISO8601 format. |
| language | string | The language of the webpage, uses ISO 639-1 language code. |
| isAdult | boolean | Indicates whether the result includes adult content. |
| clickUrl | string | Redirect URL that proxies the click through Bing. Only present when click redirect is enabled. |
| instrumentationSuffix | string | Suffix to append to the instrumentation ping URL base for this result item. Used as the K value for both the instrumentation ping URL and the `clickUrl` redirect. Present when instrumentation ping is enabled. |
| contentTier | string | The content tier of the result, describing the commercial access characteristics of the content source. Possible values: `standard` (standard content only), `entitled` (standard plus Bring Your Own License content licensed directly from publishers), `premium` (standard, entitled, and premium paid content). |

> **Note:** Values of `crawledAt` and `lastUpdatedAt` fields are optional. That is, their coverage is not 100%. You may see empty values for these fields.

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

**See also:** [Videos Search](/documentation/api-reference/videos) | [Browse](/documentation/api-reference/browse) | [News Search (Beta)](/documentation/api-reference/news) | [Images Search (Beta)](/documentation/api-reference/images) | [Classic Search (Beta)](/documentation/api-reference/classic) | [MCP](/documentation/mcp)
