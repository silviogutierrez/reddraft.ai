import {getCookieFromCookieString} from "reactivated/dist/rpc";

export const requester = async (url: string, payload: FormData) => {
    const jsonPayload = payload.get("_reactivated_rpc_json_hack");

    const {body, contentType} =
        jsonPayload != null
            ? {body: jsonPayload, contentType: "application/json"}
            : {body: payload, contentType: undefined};

    const response = await fetch(url, {
        method: "POST",
        body,
        headers: {
            ...(contentType != null ? {"Content-Type": contentType} : {}),
            "X-CSRFToken":
                getCookieFromCookieString("csrftoken", document.cookie) ?? "",
        },
    });

    return {
        data: await response.json(),
        status: response.status,
        headers: response.headers,
    };
};
