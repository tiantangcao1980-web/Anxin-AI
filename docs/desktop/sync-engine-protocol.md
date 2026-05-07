# Desktop Sync Engine Protocol

> 日期：2026-05-06

## Push

`POST /api/v1/sync/push`

Request:

```json
{
  "device_id": "desktop-a",
  "last_sync_version": 12,
  "records": [
    {
      "entity_type": "document",
      "entity_id": "doc-1",
      "action": "update",
      "data": {"title": "合同草稿"},
      "timestamp": "2026-05-06T10:00:00Z",
      "version": 3
    }
  ]
}
```

Response:

```json
{
  "accepted": 1,
  "rejected": 0,
  "conflicts": [],
  "server_version": 13
}
```

Conflict response:

```json
{
  "accepted": 0,
  "rejected": 1,
  "conflicts": [
    {
      "entity_type": "document",
      "entity_id": "doc-1",
      "local_data": {"title": "local"},
      "remote_data": {"title": "remote"},
      "local_timestamp": "2026-05-06T10:00:00Z",
      "remote_timestamp": "2026-05-06T10:01:00Z"
    }
  ],
  "server_version": 13
}
```

## Pull

`GET /api/v1/sync/pull?since_version=12&limit=500`

Response:

```json
{
  "records": [
    {
      "id": "log-id",
      "entity_type": "document",
      "entity_id": "doc-1",
      "action": "update",
      "data": {"title": "合同草稿"},
      "timestamp": "2026-05-06T10:00:00+00:00",
      "version": 3,
      "server_version": 13,
      "device_id": "desktop-a",
      "synced_at": "2026-05-06T10:00:01+00:00"
    }
  ],
  "server_version": 13,
  "has_more": false
}
```

## Resolve

`POST /api/v1/sync/resolve`

```json
{
  "entity_type": "document",
  "entity_id": "doc-1",
  "resolution": "merge",
  "merged_data": {"title": "merged"}
}
```

## Error Rules

- `401`: not authenticated.
- `422`: invalid record shape.
- `200` with rejected records: record-level conflict, not transport failure.
- Failed transport must leave desktop local records pending/failed for retry.

