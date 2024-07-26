# King of the Hill Cast Overlay

## Dependencies

```sh
pip install requests auraxium uvicorn python-socketio
```

## Run

```
python main.py
```

If running locally, browse to `http://127.0.0.1:8080`.

Browse to the `/admin` endpoint to start, pause and reset matches. To reset the match, it must first be paused.

If running in docker, you'll need to add the `host="0.0.0.0"` argument to the `uvicorn.Config()` call.

```python
config = uvicorn.Config("main:app", port=8080, log_level="info", host="0.0.0.0")
```
