# Nemotron Parse endpoint configuration

## NVIDIA Build and standalone NIM, 2026-11-23

Open [Nemotron 3.5 Parse on NVIDIA Build](https://build.nvidia.com/nvidia/nemotron-3.5-parse),
select **Get API Key**, and sign in or join the free NVIDIA Developer Program.
Generate the key and save it somewhere private. The [NVIDIA quickstart](https://docs.api.nvidia.com/nim/docs/api-quickstart)
describes the account and key flow.

Set these values in your shell or copy `.env.example` to your local `.env`:

```dotenv
NEMOPARSE_ENDPOINT=https://ai.api.nvidia.com/v1/retrieval/nvidia/nemotron-3.5-parse/parse
NEMOPARSE_API_KEY=<your NVIDIA API key>
```

For a self-hosted standalone NIM, use its full URL, such as
`http://localhost:8000/v1/parse`, and set a key if the deployment requires
one. Use the final `/parse` path to select the document API. Banyan sends
one rendered page per request and reads text, layout classes, and bounding
boxes from the response. A model name is optional for this API. The API
uses server-side decoding, so leave `--temperature` at its default and
omit `--re_run`. A response that reaches the output limit raises an error.

```sh
banyan-extract --backend nemoparse --save_bbox_data tests/data/docs/sample.pdf output/
```

The free hosted service is intended for evaluation. Use a public or
synthetic page for the first test. See
[NVIDIA's endpoint documentation](https://build.nvidia.com/nvidia/nemotron-3.5-parse/apireference)
for request details and trial terms.

## OpenAI-compatible deployments, 2026-11-23

Set `NEMOPARSE_ENDPOINT` to a chat-compatible API base URL and
`NEMOPARSE_MODEL` to the served model identifier. A private vLLM server
serving v1.2 could use the following configuration:

```dotenv
NEMOPARSE_ENDPOINT=http://localhost:8000/v1
NEMOPARSE_MODEL=nvidia/NVIDIA-Nemotron-Parse-v1.2
```

Set `NEMOPARSE_API_KEY` when the deployment uses bearer authentication.
An explicit shell key takes precedence over the key in `.env`. The
`latest` and `legacy` model-version flags still select their respective
chat request formats.
