AGENT_SCHEMA = {
    "type": "object",

    "required": [
        "agentId",
        "agentName",
        "agentDesc"
    ],

    "properties": {
        "agentId": {
            "type": "string",
            "minLength": 1
        },

        "agentName": {
            "type": "string",
            "minLength": 1
        },

        "agentDesc": {
            "type": "string"
        }
    },

    "additionalProperties": False
}

AGENT_CONFIG_RESPONSE_SCHEMA = {
    "type": "object",

    "required": [
        "code",
        "info",
        "data"
    ],

    "properties": {
        "code": {
            "type": "string"
        },

        "info": {
            "type": "string"
        },

        "data": {
            "type": "array",
            "minItems": 1,
            "items": AGENT_SCHEMA
        }
    },

    "additionalProperties": False
}

CREATE_SESSION_RESPONSE_SCHEMA = {
    "type": "object",

    "required": [
        "code",
        "info",
        "data"
    ],

    "properties": {
        "code": {
            "type": "string"
        },

        "info": {
            "type": "string"
        },

        "data": {
            "type": "object",

            "required": [
                "sessionId"
            ],

            "properties": {
                "sessionId": {
                    "type": "string",
                    "minLength": 1
                }
            },

            "additionalProperties": False
        }
    },

    "additionalProperties": False
}