from typing import (
    Any,
    ClassVar,
    Dict,
    Hashable,
    Iterable,
    Mapping,
    Optional,
    Type,
    TypeVar,
    Tuple,
)

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_CODE,
    ATTR_ID,
    ATTR_NAME,
    STATE_OFF,
    STATE_ON,
    STATE_UNKNOWN,
   
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType, StateType
from homeassistant.util import slugify

from custom_components.energosbyt_plus._base import (
    EnergosbytPlusEntity,
    make_common_async_setup_entry,
)
from custom_components.energosbyt_plus._util import dev_presentation_replacer
from custom_components.energosbyt_plus.api import Account, Payment, Work
from custom_components.energosbyt_plus.const import (
    ATTR_AMOUNT,
    ATTR_PAID_AT,
    ATTR_PERIOD,
    ATTR_SERVICES,
    CONF_LAST_PAYMENT,
    CONF_WORKS,
    DOMAIN,
    FORMAT_VAR_ID,
    FORMAT_VAR_TYPE_EN,
    FORMAT_VAR_TYPE_RU,
    ATTR_DESCRIPTION,
    ATTR_END,
    ATTR_START,
    ATTR_TYPE,   
    
)

_TEnergosbytPlusEntity = TypeVar("_TEnergosbytPlusEntity", bound=EnergosbytPlusEntity)

class EnergosbytPlusWorks(EnergosbytPlusEntity, BinarySensorEntity):
    config_key: ClassVar[str] = CONF_WORKS

    def __init__(self, *args, works: Optional[Tuple[Work]] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._works = works or ()

        self._entity_id: Optional[str] = f"binary_sensor." + slugify(
            f"{self._account.number}_works"
        )

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._works is not None  # Всегда доступен, если works не None

    @property
    def is_on(self) -> bool:
        """Return True if there are active works."""
        return bool(self._works and any(work.service for work in self._works))

    @property
    def entity_id(self) -> Optional[str]:
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value: Optional[str]) -> None:
        self._entity_id = value

    #################################################################################
    # Implementation base of inherent class
    #################################################################################

    @classmethod
    async def async_refresh_account(
        cls: Type[_TEnergosbytPlusEntity],
        hass: HomeAssistant,
        entities: Dict[Hashable, _TEnergosbytPlusEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ) -> Optional[Iterable[_TEnergosbytPlusEntity]]:
        entity_key = account.id

        try:
            entity = entities[entity_key]
        except KeyError:
            entity = cls(account, account_config)
            entities[entity_key] = entity
            return [entity]
        else:
            if entity.enabled:
                entity.async_schedule_update_ha_state(force_refresh=True)

    async def async_update_internal(self) -> None:
        """Update works data."""
        residential_object = self._account.residential_object
        if residential_object:
            self._works = await self._account.api.async_get_works(residential_object.id)
        else:
            self._works = ()           

    #################################################################################
    # Data-oriented implementation of inherent class
    #################################################################################

    @property
    def code(self) -> str:
        return self._account.number

    @property
    def state(self) -> StateType:
        if self._works is None:
            return STATE_UNKNOWN
        return STATE_ON if self.is_on else STATE_OFF

    @property
    def icon(self) -> str:
        return "mdi:tools"

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        return self.extra_state_attributes

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        if not self._works:
            # Возвращаем пустой список работ вместо None
            return {"works": []}
        
        works_attributes = []
        for work in self._works:
            work_attr = {
                ATTR_TYPE: work.type,
                ATTR_START: work.start.isoformat(),
                ATTR_END: work.end.isoformat(),
            }
            if work.description:
                work_attr[ATTR_DESCRIPTION] = work.description
            works_attributes.append(work_attr)

        return {"works": works_attributes}

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        return {
            FORMAT_VAR_ID: self._account.id,
            FORMAT_VAR_TYPE_EN: "works",
            FORMAT_VAR_TYPE_RU: "работы",
        }

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        return f"account_{self._account.id}_works"

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_works"




class EnergosbytPlusLastPayment(EnergosbytPlusEntity, BinarySensorEntity):
    config_key: ClassVar[str] = CONF_LAST_PAYMENT

    def __init__(self, *args, last_payment: Optional[Payment] = None, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._last_payment = last_payment

        self._entity_id: Optional[str] = f"binary_sensor." + slugify(
            f"{self._account.number}_last_payment"
        )

    @property
    def is_on(self) -> bool:
        payment = self._last_payment
        return payment is not None and payment.is_accepted

    @property
    def entity_id(self) -> Optional[str]:
        return self._entity_id

    @entity_id.setter
    def entity_id(self, value: Optional[str]) -> None:
        self._entity_id = value

    #################################################################################
    # Implementation base of inherent class
    #################################################################################

    @classmethod
    async def async_refresh_account(
        cls: Type[_TEnergosbytPlusEntity],
        hass: HomeAssistant,
        entities: Dict[Hashable, _TEnergosbytPlusEntity],
        account: "Account",
        config_entry: ConfigEntry,
        account_config: ConfigType,
    ) -> Optional[Iterable[_TEnergosbytPlusEntity]]:
        entity_key = account.id

        try:
            entity = entities[entity_key]

        except KeyError:
            entity = cls(account, account_config)
            entities[entity_key] = entity
            return [entity]

        else:
            if entity.enabled:
                entity.async_schedule_update_ha_state(force_refresh=True)

    async def async_update_internal(self) -> None:
        self._last_payment = await self._account.async_get_last_payment()

    #################################################################################
    # Data-oriented implementation of inherent class
    #################################################################################

    @property
    def code(self) -> str:
        return self._account.number

    @property
    def state(self) -> StateType:
        data = self._last_payment

        if data is None:
            return STATE_UNKNOWN

        return STATE_ON if self.is_on else STATE_OFF

    @property
    def icon(self) -> str:
        return "mdi:cash-multiple"

    @property
    def sensor_related_attributes(self) -> Optional[Mapping[str, Any]]:
        return self.extra_state_attributes

    @property
    def extra_state_attributes(self) -> Optional[Mapping[str, Any]]:
        payment = self._last_payment
        dev_presentation_enabled = self.is_dev_presentation_enabled

        if payment is not None:
            services_attribute = []

            for service in payment.services:
                service_attributes = {
                    ATTR_ID: service.id,
                    ATTR_CODE: service.code,
                    ATTR_NAME: service.name,
                    ATTR_AMOUNT: service.amount,
                }

                if dev_presentation_enabled:
                    dev_presentation_replacer(
                        service_attributes, (), (ATTR_AMOUNT, ATTR_ID)
                    )

                services_attribute.append(service_attributes)

            attributes = {
                ATTR_AMOUNT: payment.amount,
                ATTR_PAID_AT: payment.created_at.isoformat(),
                ATTR_SERVICES: services_attribute,
            }

            if dev_presentation_enabled:
                dev_presentation_replacer(
                    attributes,
                    (ATTR_PAID_AT, ATTR_PERIOD),
                    (ATTR_AMOUNT,),
                )

            return attributes

        return None

    @property
    def name_format_values(self) -> Mapping[str, Any]:
        last_payment = self._last_payment
        return {
            FORMAT_VAR_ID: last_payment.id if last_payment else "<?>",
            FORMAT_VAR_TYPE_EN: "last payment",
            FORMAT_VAR_TYPE_RU: "последний платёж",
        }

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        return f"account_{self._account.id}_lastpayment"

    @property
    def device_class(self) -> Optional[str]:
        return DOMAIN + "_payment"


async_setup_entry = make_common_async_setup_entry(EnergosbytPlusLastPayment, EnergosbytPlusWorks)