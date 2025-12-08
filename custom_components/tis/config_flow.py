from __future__ import annotations
import logging,voluptuous as vol
from homeassistant.config_entries import ConfigFlow,ConfigFlowResult
from homeassistant.const import CONF_PORT
from homeassistant.core import callback
from.const import DOMAIN
_LOGGER=logging.getLogger(__name__)
schema=vol.Schema({vol.Required(CONF_PORT):int},required=True)
class TISConfigFlow(ConfigFlow,domain=DOMAIN):
    VERSION=1
    async def async_step_user(C,user_input=None):
        A=user_input;B={}
        if A is not None:
            logging.info(f"recieved user input {A}");D=await C.validate_port(A[CONF_PORT])
            if not D:B['base']='invalid_port';logging.error(f"Provided port is invalid: {A}")
            if not B:return C.async_create_entry(title='TIS Control Bridge',data=A)
            else:logging.error(f"Errors occurred: {B}");return C._show_setup_form(B)
        return C._show_setup_form(errors=B)
    @callback
    def _show_setup_form(self,errors=None):A=errors;return self.async_show_form(step_id='user',data_schema=schema,errors=A if A else{})
    async def validate_port(A,port):
        if isinstance(port,int):
            if 1<=port<=65535:return True
        return False