# How to Change Things

This page is a practical developer checklist for common changes.

## Add a new field to a database-backed feature

Example workflow:

1. update the SQLAlchemy model
2. update `to_dict()`
3. update create/update Pydantic models
4. update API handlers
5. update relevant frontend template/JS
6. add lightweight migration logic if the table already exists
7. update docs in `docs/`

## Add a new MQTT topic

1. find topic parsing in `MQTTHandler.on_message`
2. add topic handling branch
3. validate payload parsing carefully
4. decide whether data belongs in an existing table or a new table
5. update UI if the new information must be visible
6. document the topic in `06-mqtt-data-flow.md`

## Add a new HTML page

1. create `templates/<page>.html`
2. create `static/js/<page>.js`
3. create `static/css/<page>.css` if needed
4. add route in `backend/main.py`
5. add nav link
6. document the page in `02-web-ui.md`

## Add a new material pricing model

1. define the model name in backend logic
2. decide which inputs are required
3. update Katalog page forms if necessary
4. update Laufzettel material modal behavior
5. store enough data for historical price traceability
6. document the formula in `04-material-katalog.md`

## Add a new docs page

1. add a new numbered Markdown file in `docs/`
2. use a top-level `#` heading
3. keep the page focused on one topic
4. link to related docs where helpful
5. the docs app will pick it up automatically
