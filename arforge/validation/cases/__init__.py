"""Central validation case registry for the domain-organized case modules.

This module re-exports the case classes and defines the ordered `core`
ruleset used by semantic validation.
"""

from __future__ import annotations

from typing import List

from ...semantic_validation import ValidationCase
from .common import DuplicateNameCase
from .connectivity import (
    CsPortConnectivityCase,
    CsPortUsageCase,
    DeclaredPortUsageCase,
    ModeSwitchConnectivityCase,
    ModeSwitchUsageCase,
    SrMultiplicityCase,
    SrPortConnectivityCase,
    SrPortUsageCase,
)
from .interfaces import InterfaceSemanticCase
from .package_layout import PackageLayoutCase
from .modes import (
    ModeDeclarationGroupInitialModeCase,
    ModeDeclarationGroupStructureCase,
    UnusedModeDeclarationGroupCase,
)
from .swc import (
    ComSpecSemanticCase,
    DataReceiveEventCase,
    ModeConditionCase,
    ModeSwitchEventCase,
    OperationInvokedEventCase,
    RunnableAccessSemanticCase,
    RunnableRaisedErrorCase,
    RunnableTriggerPolicyCase,
    SwcPortInterfaceCase,
    SwcStructureCase,
)
from .system import (
    ConnectionSemanticCase,
    SubcompositionConnectionSemanticCase,
    SubcompositionDelegationConnectorCase,
    SubcompositionPortDefinitionCase,
    SubcompositionTypeCase,
    SystemInstanceTypeCase,
)
from .timing import SrConsumerFasterThanProducerCase, SrProducerFasterThanConsumerCase
from .types import ApplicationConstraintCase, BaseTypeMetadataCase

__all__ = [
    "ApplicationConstraintCase",
    "BaseTypeMetadataCase",
    "ComSpecSemanticCase",
    "ConnectionSemanticCase",
    "CsPortConnectivityCase",
    "CsPortUsageCase",
    "DataReceiveEventCase",
    "DeclaredPortUsageCase",
    "DuplicateNameCase",
    "InterfaceSemanticCase",
    "ModeConditionCase",
    "ModeDeclarationGroupInitialModeCase",
    "ModeDeclarationGroupStructureCase",
    "ModeSwitchConnectivityCase",
    "ModeSwitchEventCase",
    "ModeSwitchUsageCase",
    "OperationInvokedEventCase",
    "PackageLayoutCase",
    "RunnableAccessSemanticCase",
    "RunnableRaisedErrorCase",
    "RunnableTriggerPolicyCase",
    "SrMultiplicityCase",
    "SrConsumerFasterThanProducerCase",
    "SrPortConnectivityCase",
    "SrPortUsageCase",
    "SrProducerFasterThanConsumerCase",
    "SwcPortInterfaceCase",
    "SwcStructureCase",
    "SubcompositionConnectionSemanticCase",
    "SubcompositionDelegationConnectorCase",
    "SubcompositionPortDefinitionCase",
    "SubcompositionTypeCase",
    "SystemInstanceTypeCase",
    "UnusedModeDeclarationGroupCase",
    "core_validation_cases",
]


def core_validation_cases() -> List[ValidationCase]:
    return [
        DuplicateNameCase(),
        BaseTypeMetadataCase(),
        PackageLayoutCase(),
        InterfaceSemanticCase(),
        ModeDeclarationGroupStructureCase(),
        ModeDeclarationGroupInitialModeCase(),
        UnusedModeDeclarationGroupCase(),
        ApplicationConstraintCase(),
        SwcStructureCase(),
        SwcPortInterfaceCase(),
        RunnableAccessSemanticCase(),
        OperationInvokedEventCase(),
        RunnableTriggerPolicyCase(),
        ComSpecSemanticCase(),
        RunnableRaisedErrorCase(),
        DataReceiveEventCase(),
        ModeSwitchEventCase(),
        ModeConditionCase(),
        SystemInstanceTypeCase(),
        SubcompositionTypeCase(),
        SubcompositionPortDefinitionCase(),
        SubcompositionDelegationConnectorCase(),
        SubcompositionConnectionSemanticCase(),
        ConnectionSemanticCase(),
        SrPortConnectivityCase(),
        SrPortUsageCase(),
        CsPortConnectivityCase(),
        CsPortUsageCase(),
        SrMultiplicityCase(),
        ModeSwitchConnectivityCase(),
        DeclaredPortUsageCase(),
        ModeSwitchUsageCase(),
        SrConsumerFasterThanProducerCase(),
        SrProducerFasterThanConsumerCase(),
    ]
