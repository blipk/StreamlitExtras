import Cookies from "universal-cookie"
import { Streamlit } from "streamlit-component-lib"

let lastOutput = null
/*eslint-disable */
// Called after successful set and remove
// const changeListener = (params) => {
//   const { name, value, options } = params
//   console.log(name, value, options)
// }
const cookies = new Cookies()
// cookies.addChangeListener(changeListener)
parent["CookieManager"] = cookies
window["CookieManager"] = cookies
/*eslint-enable */

const CookieManager = (event) => {
    const { args, disabled, theme } = event.detail
    const { method, options = {} } = args
    const { name, value, expires, sameSite, secure, path } = options
    const defaultExpiryMinutes = 720
    const defaultedOptions = {
        "name": name,
        "value": value,
        "expires": new Date(expires) || new Date(new Date().getTime() + defaultExpiryMinutes * 60000),
        "sameSite": sameSite || "strict",
        "secure": secure || true,
        "path": path || "/",
        //"maxAge"
        //"domain"
        //"httpOnly"
    }

    const removeOptions = { path: defaultedOptions.path, sameSite: defaultedOptions.sameSite }
    const output =
        method === "set" ? cookies.set(name, value, defaultedOptions) || true
            : method === "get" ? cookies.get(name)
            : method === "getAll" ? cookies.getAll()
            : method === "delete" ? cookies.remove(name, removeOptions) || true
            : null

    if (output && JSON.stringify(lastOutput) != JSON.stringify(output)) {
        lastOutput = output
        Streamlit.setComponentValue(output)
        Streamlit.setComponentReady()
    }

    Streamlit.setFrameHeight(0)
}

Streamlit.events.addEventListener(Streamlit.RENDER_EVENT, CookieManager)
Streamlit.setComponentReady()
Streamlit.setFrameHeight(0)
