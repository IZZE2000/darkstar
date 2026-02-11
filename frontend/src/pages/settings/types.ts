export type FieldType =
    | 'number'
    | 'text'
    | 'boolean'
    | 'entity'
    | 'service'
    | 'select'
    | 'array'
    | 'azimuth'
    | 'tilt'
    | 'solar_arrays'
    | 'penalty_levels'
    | 'entity_array'
    | 'info'

export interface HaEntity {
    entity_id: string
    friendly_name: string
    domain: string
}

export interface BaseField {
    key: string
    label: string
    helper?: string
    path: string[]
    type: FieldType
    options?: { label: string; value: string }[]
    companionKey?: string
    disabled?: boolean
    notImplemented?: boolean
    required?: boolean
    /** Conditional visibility based on a single config key */
    showIf?: {
        configKey: string // e.g., 'system.has_water_heater'
        value?: string | boolean | number | (string | boolean | number)[] // expected value(s)
        disabledText?: string // overlay text when disabled
    }
    /** All config keys must be truthy for field to be enabled */
    showIfAll?: string[]
    /** Any config key must be truthy for field to be enabled */
    showIfAny?: string[]
    /** Flags this field as hidden unless Advanced Mode is enabled */
    isAdvanced?: boolean
    /** Subsection grouping within a card */
    subsection?: string
    /** Custom CSS classes for the field wrapper (e.g., col-span-2) */
    className?: string
    /** For entity_array type: specifies which entity type to manage */
    entityType?: 'water_heater' | 'ev_charger'
}

export interface InverterProfile {
    name: string
    description: string
    supported_brands: string[]
    version: string
    capabilities: {
        grid_charging_control: boolean
        watts_based_control: boolean
        service_call_mode: boolean
        separate_grid_charging_switch: boolean
        supports_export_mode: boolean
        supports_zero_export: boolean
        supports_self_consumption: boolean
        supports_soc_target: boolean
        supports_grid_export_limit: boolean
        supports_force_discharge: boolean
    }
    behavior: {
        control_unit: 'A' | 'W'
    }
    entities: {
        required: Record<string, string | null>
        optional: Record<string, string | null>
    }
}

export interface SettingsSection<T extends BaseField = BaseField> {
    title: string
    description: string
    isHA?: boolean
    fields: T[]
    /** Section-level conditional visibility */
    showIf?: {
        configKey: string
        value?: string | boolean | number | (string | boolean | number)[]
    }
}

export const systemSections: SettingsSection[] = [
    {
        title: 'System Profile',
        description: 'Core hardware toggles. ⚠️ Non-Deye profiles are currently Work In Progress.',
        fields: [
            {
                key: 'system.inverter_profile',
                label: 'Inverter Profile',
                path: ['system', 'inverter_profile'],
                type: 'select',
                options: [
                    { label: 'Generic (Standard)', value: 'generic' },
                    { label: 'Deye / SunSynk', value: 'deye' },
                    { label: 'Fronius', value: 'fronius' },
                    { label: 'Victron', value: 'victron' },
                ],
                helper: 'Select your inverter brand. Note: Only Deye/SunSynk is fully supported. Others are experimental.',
            },
            {
                key: 'system.has_solar',
                label: 'Solar panels installed',
                path: ['system', 'has_solar'],
                type: 'boolean',
            },
            {
                key: 'system.has_battery',
                label: 'Home battery installed',
                path: ['system', 'has_battery'],
                type: 'boolean',
            },
            {
                key: 'system.has_water_heater',
                label: 'Smart water heater',
                path: ['system', 'has_water_heater'],
                type: 'boolean',
            },
            {
                key: 'system.has_ev_charger',
                label: 'EV charger installed',
                path: ['system', 'has_ev_charger'],
                type: 'boolean',
            },
            {
                key: 'executor.inverter.control_unit',
                label: 'Control Unit',
                path: ['executor', 'inverter', 'control_unit'],
                type: 'select',
                options: [
                    { label: 'Amperes (A)', value: 'A' },
                    { label: 'Watts (W)', value: 'W' },
                ],
                helper: 'Unit used for inverter control commands.',
                required: true,
            },

            {
                key: 'system.grid_meter_type',
                label: 'Grid Meter Type',
                path: ['system', 'grid_meter_type'],
                type: 'select',
                options: [
                    { label: 'Net Meter (Single Sensor)', value: 'net' },
                    { label: 'Dual Meter (Separate Import/Export)', value: 'dual' },
                ],
                helper: 'Select "Net" if you have one sensor (+/-). Select "Dual" if you have separate import/export sensors.',
            },
            {
                key: 'export.enable_export',
                label: 'Enable grid export',
                path: ['export', 'enable_export'],
                type: 'boolean',
                helper: 'If disabled, the planner will enforce zero export to the grid.',
            },
        ],
    },
    {
        title: 'Location & Solar Array',
        description: 'Geolocation and PV array parameters used by the forecasting engine.',
        fields: [
            {
                key: 'system.location.latitude',
                label: 'Latitude',
                helper: 'Decimal degrees, positive north. Example: 55.4932',
                path: ['system', 'location', 'latitude'],
                type: 'number',
            },
            {
                key: 'system.location.longitude',
                label: 'Longitude',
                helper: 'Decimal degrees, positive east. Example: 13.1112',
                path: ['system', 'location', 'longitude'],
                type: 'number',
            },
            {
                key: 'system.solar_arrays',
                label: 'Solar Arrays',
                path: ['system', 'solar_arrays'],
                type: 'solar_arrays',
                helper: 'Configure up to 6 solar arrays with different orientations.',
                showIf: {
                    configKey: 'system.has_solar',
                    value: true,
                    disabledText: "Enable 'Solar panels installed' in System Profile to configure",
                },
            },
        ],
    },
    {
        title: 'Battery Specifications',
        description: 'Capacity, max power, and SoC limits define safe operating bands.',
        fields: [
            {
                key: 'battery.capacity_kwh',
                label: 'Battery capacity (kWh)',
                helper: 'Total usable capacity of your battery bank.',
                path: ['battery', 'capacity_kwh'],
                type: 'number',
            },
            {
                key: 'battery.max_charge_a',
                label: 'Max charge current (A)',
                helper: 'Maximum charging current allowed from grid.',
                path: ['battery', 'max_charge_a'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'battery.max_charge_w',
                label: 'Max charge power (W)',
                helper: 'Maximum charging power allowed from grid.',
                path: ['battery', 'max_charge_w'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'W',
                },
            },
            {
                key: 'battery.max_discharge_a',
                label: 'Max discharge current (A)',
                helper: 'Maximum discharge current for load following.',
                path: ['battery', 'max_discharge_a'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'battery.max_discharge_w',
                label: 'Max discharge power (W)',
                helper: 'Maximum discharge power for load following.',
                path: ['battery', 'max_discharge_w'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'W',
                },
            },
            {
                key: 'battery.nominal_voltage_v',
                label: 'Nominal Voltage (V)',
                helper: 'Used for Ampere-to-kW calculations in the Planner.',
                path: ['battery', 'nominal_voltage_v'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'battery.min_voltage_v',
                label: 'Worst-case Voltage (V)',
                helper: 'Min safe voltage used by Executor for amperage safety.',
                path: ['battery', 'min_voltage_v'],
                type: 'number',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'battery.min_soc_percent',
                label: 'Min SoC (%)',
                path: ['battery', 'min_soc_percent'],
                type: 'number',
            },
            {
                key: 'executor.override.low_soc_export_floor',
                label: 'Export Prevention Floor (%)',
                helper: 'Minimum SoC to allow battery export. Prevents discharging to grid when battery is low.',
                path: ['executor', 'override', 'low_soc_export_floor'],
                type: 'number',
            },
            {
                key: 'battery.max_soc_percent',
                label: 'Max SoC (%)',
                path: ['battery', 'max_soc_percent'],
                type: 'number',
            },
            {
                key: 'battery_economics.battery_cycle_cost_kwh',
                label: 'Battery cycle cost (SEK/kWh)',
                helper: 'Estimated degradation cost for every kWh cycled. Affects arbitrage profitability.',
                path: ['battery_economics', 'battery_cycle_cost_kwh'],
                type: 'number',
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'system.grid.max_power_kw',
                label: 'HARD Grid max power (kW)',
                path: ['system', 'grid', 'max_power_kw'],
                type: 'number',
            },
            {
                key: 'grid.import_limit_kw',
                label: 'Soft import limit (kW) [NOT IMPLEMENTED]',
                path: ['grid', 'import_limit_kw'],
                type: 'number',
            },
        ],
    },
    {
        title: 'Pricing & Timezone',
        description: 'Nordpool zone and local timezone for planner calculations.',
        fields: [
            {
                key: 'nordpool.price_area',
                label: 'Nordpool Price Area',
                helper: 'e.g. SE4, NO1, DK2',
                path: ['nordpool', 'price_area'],
                type: 'text',
            },
            { key: 'pricing.vat_percent', label: 'VAT (%)', path: ['pricing', 'vat_percent'], type: 'number' },
            {
                key: 'pricing.grid_transfer_fee_sek',
                label: 'Grid transfer fee (SEK/kWh)',
                helper: 'Fee paid to your grid operator for power delivery.',
                path: ['pricing', 'grid_transfer_fee_sek'],
                type: 'number',
            },
            {
                key: 'pricing.energy_tax_sek',
                label: 'Energy tax (SEK/kWh)',
                path: ['pricing', 'energy_tax_sek'],
                type: 'number',
            },
            {
                key: 'pricing.subscription_fee_sek_per_month',
                label: 'Monthly subscription fee (SEK)',
                helper: 'Fixed monthly grid connection fee.',
                path: ['pricing', 'subscription_fee_sek_per_month'],
                type: 'number',
            },
            { key: 'timezone', label: 'Timezone', path: ['timezone'], type: 'text' },
        ],
    },
    {
        title: '── Home Assistant Connection ──',
        isHA: true,
        description: 'Connection parameters for your Home Assistant instance.',
        fields: [
            {
                key: 'home_assistant.url',
                label: 'HA URL',
                helper: 'e.g. http://homeassistant.local:8123',
                path: ['home_assistant', 'url'],
                type: 'text',
            },
            {
                key: 'home_assistant.token',
                label: 'Long-Lived Access Token',
                path: ['home_assistant', 'token'],
                type: 'text',
            },
        ],
    },
    {
        title: 'Required HA Input Sensors',
        isHA: true,
        description: 'Core sensors Darkstar reads from Home Assistant.',
        fields: [
            {
                key: 'input_sensors.battery_soc',
                label: 'Battery SoC (%)',
                path: ['input_sensors', 'battery_soc'],
                type: 'entity',
                helper: 'Core sensor. Required for planner SoC targeting.',
                required: true,
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.pv_power',
                label: 'PV Power (W/kW)',
                path: ['input_sensors', 'pv_power'],
                type: 'entity',
                helper: 'Used by executor for PV dump detection and recorder for history.',
                showIf: {
                    configKey: 'system.has_solar',
                    value: true,
                    disabledText: "Enable 'Solar panels installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.load_power',
                label: 'Load Power (W/kW)',
                path: ['input_sensors', 'load_power'],
                type: 'entity',
                helper: 'Used by executor for system state and Aurora training.',
            },
            {
                key: 'input_sensors.water_power',
                label: 'Water Heater Power (W/kW)',
                path: ['input_sensors', 'water_power'],
                type: 'entity',
                helper: 'Power sensor of the water heater element. Used for live metrics and history.',
                subsection: 'Water Heater',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.water_heater_consumption',
                label: 'Water Heater Daily Energy',
                path: ['input_sensors', 'water_heater_consumption'],
                type: 'entity',
                helper: 'Total energy consumed by the water heater today. Used for quota tracking.',
                subsection: 'Water Heater',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            // EV Charger Input Sensors
            {
                key: 'input_sensors.ev_soc',
                label: 'EV State of Charge (%)',
                path: ['input_sensors', 'ev_soc'],
                type: 'entity',
                helper: 'Current state of charge of the EV battery. Required for EV charging optimization.',
                subsection: 'EV Charger',
                showIf: {
                    configKey: 'system.has_ev_charger',
                    value: true,
                    disabledText: "Enable 'EV charger installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.ev_plug',
                label: 'EV Plug Status',
                path: ['input_sensors', 'ev_plug'],
                type: 'entity',
                helper: 'Binary sensor indicating if the EV is plugged in. Triggers re-planning when car connects.',
                subsection: 'EV Charger',
                showIf: {
                    configKey: 'system.has_ev_charger',
                    value: true,
                    disabledText: "Enable 'EV charger installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.ev_power',
                label: 'EV Charging Power (W/kW)',
                path: ['input_sensors', 'ev_power'],
                type: 'entity',
                helper: 'Current charging power of the EV. Used for live metrics and power flow display.',
                subsection: 'EV Charger',
                showIf: {
                    configKey: 'system.has_ev_charger',
                    value: true,
                    disabledText: "Enable 'EV charger installed' in System Profile to configure",
                },
            },
        ],
    },
    {
        title: 'Required HA Control Entities',
        isHA: true,
        description: 'Entities Darkstar writes to for control.',
        fields: [
            {
                key: 'executor.inverter.work_mode',
                label: 'Work Mode Selector',
                path: ['executor', 'inverter', 'work_mode'],
                type: 'entity',
                helper: 'Darkstar sets inverter mode (Export/Zero-Export).',
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'executor.inverter.max_charge_current',
                label: 'Max Charge Current',
                path: ['executor', 'inverter', 'max_charge_current'],
                type: 'entity',
                helper: 'Darkstar sets charge rate in Amps.',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'executor.inverter.max_charge_power',
                label: 'Max Charge Power',
                path: ['executor', 'inverter', 'max_charge_power'],
                type: 'entity',
                helper: 'Darkstar sets charge rate in Watts.',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'W',
                },
            },
            {
                key: 'executor.inverter.max_discharge_current',
                label: 'Max Discharge Current',
                path: ['executor', 'inverter', 'max_discharge_current'],
                type: 'entity',
                helper: 'Darkstar sets discharge rate in Amps.',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'A',
                },
            },
            {
                key: 'executor.inverter.max_discharge_power',
                label: 'Max Discharge Power',
                path: ['executor', 'inverter', 'max_discharge_power'],
                type: 'entity',
                helper: 'Darkstar sets discharge rate in Watts.',
                showIf: {
                    configKey: 'executor.inverter.control_unit',
                    value: 'W',
                },
            },
            {
                key: 'executor.inverter.grid_max_export_power',
                label: 'Max Grid Export (W)',
                helper: 'HA Number entity to control grid export limit in Watts.',
                path: ['executor', 'inverter', 'grid_max_export_power'],
                type: 'entity',
                showIf: {
                    configKey: 'export.enable_export',
                    disabledText: 'Enable "Grid Export" in System Profile to configure',
                },
            },
            {
                key: 'executor.inverter.grid_max_export_power_switch',
                label: 'Max Grid Export Switch',
                helper: 'HA Switch entity to enable/disable grid export limit.',
                path: ['executor', 'inverter', 'grid_max_export_power_switch'],
                type: 'entity',
                showIf: {
                    configKey: 'export.enable_export',
                    disabledText: 'Enable "Grid Export" in System Profile to configure',
                },
            },
            {
                key: 'executor.water_heater.target_entity',
                label: 'Water Heater Setpoint',
                path: ['executor', 'water_heater', 'target_entity'],
                type: 'entity',
                helper: 'Thermostat entity that controls the water heater target temperature.',
                subsection: 'Water Heater',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            // EV Charger Control Entities
            {
                key: 'executor.ev_charger.switch_entity',
                label: 'EV Charger Switch',
                path: ['executor', 'ev_charger', 'switch_entity'],
                type: 'entity',
                helper: 'Switch entity to enable/disable EV charging. Darkstar will turn this on when scheduled to charge.',
                subsection: 'EV Charger',
                showIf: {
                    configKey: 'system.has_ev_charger',
                    value: true,
                    disabledText: "Enable 'EV charger installed' in System Profile to configure",
                },
            },
        ],
    },
    {
        title: 'Optional HA Input Sensors',
        isHA: true,
        description: 'Optional sensors for monitoring, Smart Home integration, and statistics.',
        fields: [
            // Power Flow & Dashboard
            {
                key: 'input_sensors.battery_power',
                label: 'Battery Power (W/kW)',
                helper: 'Positive = charging, negative = discharging',
                path: ['input_sensors', 'battery_power'],
                type: 'entity',
                companionKey: 'input_sensors.battery_power_inverted',
                subsection: 'Power Flow & Dashboard',
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.grid_power',
                label: 'Net Grid Power (W/kW)',
                helper: 'Positive = import, negative = export. Required for Net Meter mode.',
                path: ['input_sensors', 'grid_power'],
                type: 'entity',
                companionKey: 'input_sensors.grid_power_inverted',
                subsection: 'Power Flow & Dashboard',
                showIf: {
                    configKey: 'system.grid_meter_type',
                    value: 'net',
                    disabledText: 'Enable "Net Meter" in System Profile to configure',
                },
            },
            {
                key: 'input_sensors.grid_import_power',
                label: 'Grid Import Power (W/kW)',
                helper: 'Required for Dual Meter mode.',
                path: ['input_sensors', 'grid_import_power'],
                type: 'entity',
                subsection: 'Power Flow & Dashboard',
                showIf: {
                    configKey: 'system.grid_meter_type',
                    value: 'dual',
                    disabledText: 'Enable "Dual Meter" in System Profile to configure',
                },
            },
            {
                key: 'input_sensors.grid_export_power',
                label: 'Grid Export Power (W/kW)',
                helper: 'Required for Dual Meter mode.',
                path: ['input_sensors', 'grid_export_power'],
                type: 'entity',
                subsection: 'Power Flow & Dashboard',
                showIf: {
                    configKey: 'export.enable_export',
                    disabledText: 'Enable "Grid Export" in System Profile to configure',
                },
            },

            // Smart Home Integration
            {
                key: 'input_sensors.vacation_mode',
                label: 'Vacation Mode Toggle',
                path: ['input_sensors', 'vacation_mode'],
                type: 'entity',
                helper: 'Reduces water heating quota when active.',
                subsection: 'Smart Home Integration',
            },
            {
                key: 'input_sensors.alarm_state',
                label: 'Alarm Control Panel',
                path: ['input_sensors', 'alarm_state'],
                type: 'entity',
                helper: 'Enables emergency reserve boost when armed.',
                subsection: 'Smart Home Integration',
            },

            // User Override Toggles (READS)
            {
                key: 'executor.automation_toggle_entity',
                label: 'Automation Toggle',
                path: ['executor', 'automation_toggle_entity'],
                type: 'entity',
                helper: 'When OFF, executor skips all inverter actions.',
                subsection: 'User Override Toggles',
            },
            {
                key: 'executor.manual_override_entity',
                label: 'Manual Override Toggle',
                path: ['executor', 'manual_override_entity'],
                type: 'entity',
                helper: 'Triggers manual override mode in executor.',
                subsection: 'User Override Toggles',
            },

            // Today's Energy Stats
            {
                key: 'input_sensors.today_battery_charge',
                label: "Today's Battery Charge (kWh)",
                path: ['input_sensors', 'today_battery_charge'],
                type: 'entity',
                subsection: "Today's Energy Stats",
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.today_pv_production',
                label: "Today's PV Production (kWh)",
                path: ['input_sensors', 'today_pv_production'],
                type: 'entity',
                subsection: "Today's Energy Stats",
                showIf: {
                    configKey: 'system.has_solar',
                    value: true,
                    disabledText: "Enable 'Solar panels installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.today_load_consumption',
                label: "Today's Load Consumption (kWh)",
                path: ['input_sensors', 'today_load_consumption'],
                type: 'entity',
                subsection: "Today's Energy Stats",
            },
            {
                key: 'input_sensors.today_grid_import',
                label: "Today's Grid Import (kWh)",
                path: ['input_sensors', 'today_grid_import'],
                type: 'entity',
                subsection: "Today's Energy Stats",
            },
            {
                key: 'input_sensors.today_grid_export',
                label: "Today's Grid Export (kWh)",
                path: ['input_sensors', 'today_grid_export'],
                type: 'entity',
                subsection: "Today's Energy Stats",
                showIf: {
                    configKey: 'export.enable_export',
                    disabledText: 'Enable "Grid Export" in System Profile to configure',
                },
            },
            {
                key: 'input_sensors.today_net_cost',
                label: "Today's Net Cost",
                path: ['input_sensors', 'today_net_cost'],
                type: 'entity',
                subsection: "Today's Energy Stats",
            },

            // Lifetime Energy Totals
            {
                key: 'input_sensors.total_battery_charge',
                label: 'Total Battery Charge (kWh)',
                path: ['input_sensors', 'total_battery_charge'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.total_battery_discharge',
                label: 'Total Battery Discharge (kWh)',
                path: ['input_sensors', 'total_battery_discharge'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
            {
                key: 'input_sensors.total_grid_export',
                label: 'Total Grid Export (kWh)',
                path: ['input_sensors', 'total_grid_export'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
                showIf: {
                    configKey: 'export.enable_export',
                    disabledText: 'Enable "Grid Export" in System Profile to configure',
                },
            },
            {
                key: 'input_sensors.total_grid_import',
                label: 'Total Grid Import (kWh)',
                path: ['input_sensors', 'total_grid_import'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
            },
            {
                key: 'input_sensors.total_load_consumption',
                label: 'Total Load Consumption (kWh)',
                path: ['input_sensors', 'total_load_consumption'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
            },
            {
                key: 'input_sensors.total_pv_production',
                label: 'Total PV Production (kWh)',
                path: ['input_sensors', 'total_pv_production'],
                type: 'entity',
                subsection: 'Lifetime Energy Totals',
                showIf: {
                    configKey: 'system.has_solar',
                    value: true,
                    disabledText: "Enable 'Solar panels installed' in System Profile to configure",
                },
            },
        ],
    },
]

export const parameterSections: SettingsSection[] = [
    {
        title: 'Forecasting & Strategy',

        description: 'Tuning the AI forecasting engine and safety margins.',
        fields: [
            {
                key: 'forecasting.pv_confidence_percent',
                label: 'PV Confidence (%)',
                helper: '100 = trust forecast fully. Lower values make the planner more conservative with solar.',
                path: ['forecasting', 'pv_confidence_percent'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'forecasting.load_safety_margin_percent',
                label: 'Load Safety Margin (%)',
                helper: '100 = neutral. >100 = expect more load than predicted (safer).',
                path: ['forecasting', 'load_safety_margin_percent'],
                type: 'number',
                isAdvanced: true,
            },
        ],
    },
    {
        title: 'Arbitrage & Economics',
        description: 'Export thresholds, peak-only export, and degradation costs.',
        fields: [
            {
                key: 'kepler.curtailment_penalty_sek',
                label: 'Curtailment Penalty (SEK)',
                helper: 'Penalty for wasting available solar power when battery is not full (higher = more aggressive charging).',
                path: ['kepler', 'curtailment_penalty_sek'],
                type: 'number',
                subsection: 'Advanced Tuning',
                isAdvanced: true,
            },
            {
                key: 'kepler.ramping_cost_sek_per_kw',
                label: 'Ramping Cost (SEK/kW)',
                helper: 'Penalty for rapid battery power changes (higher = smoother power flow, reduces "sawtooth" behavior).',
                path: ['kepler', 'ramping_cost_sek_per_kw'],
                type: 'number',
                subsection: 'Advanced Tuning',
                isAdvanced: true,
            },
        ],
    },

    // EV Charger Settings (Legacy - global settings)
    {
        title: 'EV Charger',
        description: 'Global EV charging settings: penalty levels, replanning triggers, and charging behavior.',
        showIf: {
            configKey: 'system.has_ev_charger',
            value: true,
        },
        fields: [
            {
                key: 'ev_charger.penalty_levels',
                label: 'Penalty Levels (Urgency)',
                path: ['ev_charger', 'penalty_levels'],
                type: 'penalty_levels',
                className: 'col-span-1 sm:row-span-3',
                helper: 'Define willingness to pay at different SoC levels. Higher penalties force charging regardless of price.',
            },
            {
                key: 'ev_charger.replan_on_plugin',
                label: 'Re-plan on plug-in',
                path: ['ev_charger', 'replan_on_plugin'],
                type: 'boolean',
                helper: 'Trigger immediate re-planning when the EV is plugged in.',
                className: 'col-span-1',
            },
            {
                key: 'ev_charger.replan_on_unplug',
                label: 'Re-plan on unplug',
                path: ['ev_charger', 'replan_on_unplug'],
                type: 'boolean',
                helper: 'Trigger re-planning when the EV is unplugged.',
                className: 'col-span-1',
            },
            {
                key: 'ev_charger.info_box',
                label: 'Willingness to Pay',
                path: [], // Virtual field for UI only
                type: 'info',
                className: 'col-span-1',
            },
        ],
    },
    // ARC15: Entity-Centric EV Chargers (replaces ev_charger section)
    {
        title: 'EV Chargers',
        description: 'Configure multiple EV chargers for optimization and load disaggregation.',
        showIf: {
            configKey: 'system.has_ev_charger',
            value: true,
        },
        fields: [
            {
                key: 'ev_chargers',
                label: 'EV Chargers',
                path: ['ev_chargers'],
                type: 'entity_array',
                entityType: 'ev_charger',
                className: 'col-span-2',
                helper: 'Add and configure EV chargers for optimization. Each charger needs a unique ID, name, power rating, and sensor.',
            },
        ],
    },
    {
        title: 'Water Heating',
        description: 'Quota, deferral, and sizing controls for the water heater scheduler.',
        fields: [
            {
                key: 'water_heating.defer_up_to_hours',
                label: 'Max defer hours',
                path: ['water_heating', 'defer_up_to_hours'],
                type: 'number',
                isAdvanced: true,
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.spacing_penalty_sek',
                label: 'Spacing penalty (SEK)',
                path: ['water_heating', 'spacing_penalty_sek'],
                type: 'number',
                isAdvanced: true,
                helper: 'Penalty applied when heating sessions are too close.',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.enable_top_ups',
                label: 'Enable spaced top-ups',
                path: ['water_heating', 'enable_top_ups'],
                type: 'boolean',
                helper: 'Enable small top-up heating blocks to maintain temperature. Disable for bulk heating only.',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },

            {
                key: 'water_heating.block_start_penalty_sek',
                label: 'Block start penalty (SEK)',
                helper: 'Penalty per heating start (higher = more consolidated bulk heating).',
                path: ['water_heating', 'block_start_penalty_sek'],
                type: 'number',
                subsection: 'Advanced Tuning',
                isAdvanced: true,
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.reliability_penalty_sek',
                label: 'Reliability Penalty (SEK)',
                helper: 'Heavy penalty for failing to meet the daily min kWh quota (higher = stricter quota enforcement).',
                path: ['water_heating', 'reliability_penalty_sek'],
                type: 'number',
                subsection: 'Advanced Tuning',
                isAdvanced: true,
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.block_penalty_sek',
                label: 'Block Penalty (SEK)',
                helper: 'Small penalty per active heating slot (higher = encourages shorter, more efficient heat blocks).',
                path: ['water_heating', 'block_penalty_sek'],
                type: 'number',
                subsection: 'Advanced Tuning',
                isAdvanced: true,
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'executor.water_heater.temp_off',
                label: 'Temp: Off/Idle (°C)',
                helper: 'Target temperature when not heating (legionella safety min).',
                path: ['executor', 'water_heater', 'temp_off'],
                type: 'number',
            },
            {
                key: 'executor.water_heater.temp_normal',
                label: 'Temp: Normal (°C)',
                helper: 'Target temperature for regular scheduled heating.',
                path: ['executor', 'water_heater', 'temp_normal'],
                type: 'number',
            },
            {
                key: 'executor.water_heater.temp_boost',
                label: 'Temp: Boost (°C)',
                helper: 'Target temperature for manual boost / spa mode.',
                path: ['executor', 'water_heater', 'temp_boost'],
                type: 'number',
            },
            {
                key: 'executor.water_heater.temp_max',
                label: 'Temp: Max/PV Dump (°C)',
                helper: 'Max safe temperature for dumping excess solar PV.',
                path: ['executor', 'water_heater', 'temp_max'],
                type: 'number',
            },
            {
                key: 'executor.override.excess_pv_threshold_kw',
                label: 'PV Dump Threshold (kW)',
                helper: 'Surplus PV power required to trigger water heating as a PV dump.',
                path: ['executor', 'override', 'excess_pv_threshold_kw'],
                type: 'number',
                subsection: 'PV Dump Control',
                showIfAll: ['system.has_solar', 'system.has_water_heater'],
            },
        ],
    },
    {
        title: 'Water Heater Vacation Mode',
        description: 'Anti-legionella safety cycle when vacation mode is active.',
        fields: [
            {
                key: 'water_heating.vacation_mode.enabled',
                label: 'Enable Vacation Mode',
                path: ['water_heating', 'vacation_mode', 'enabled'],
                type: 'boolean',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.vacation_mode.anti_legionella_temp_c',
                label: 'Safety Cycle Temp (°C)',
                path: ['water_heating', 'vacation_mode', 'anti_legionella_temp_c'],
                type: 'number',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.vacation_mode.anti_legionella_interval_days',
                label: 'Safety Cycle Interval (days)',
                path: ['water_heating', 'vacation_mode', 'anti_legionella_interval_days'],
                type: 'number',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
            {
                key: 'water_heating.vacation_mode.anti_legionella_duration_hours',
                label: 'Safety Cycle Duration (hours)',
                path: ['water_heating', 'vacation_mode', 'anti_legionella_duration_hours'],
                type: 'number',
                showIf: {
                    configKey: 'system.has_water_heater',
                    value: true,
                    disabledText: "Enable 'Smart water heater' in System Profile to configure",
                },
            },
        ],
    },
    // ARC15: Entity-Centric Water Heaters (replaces water_heating section)
    {
        title: 'Water Heaters',
        description: 'Configure multiple water heaters for optimization and load disaggregation.',
        showIf: {
            configKey: 'system.has_water_heater',
            value: true,
        },
        fields: [
            {
                key: 'water_heaters',
                label: 'Water Heaters',
                path: ['water_heaters'],
                type: 'entity_array',
                entityType: 'water_heater',
                className: 'col-span-2',
                helper: 'Add and configure water heaters for optimization. Each heater needs a unique ID, name, power rating, and sensor.',
            },
        ],
    },
    {
        title: 'Learning Parameter Limits',
        description: 'Limits that keep learning adjustments conservative.',
        fields: [
            {
                key: 'learning.min_sample_threshold',
                label: 'Min sample threshold',
                path: ['learning', 'min_sample_threshold'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.min_improvement_threshold',
                label: 'Min improvement (%)',
                path: ['learning', 'min_improvement_threshold'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.battery_use_margin_sek',
                label: 'Battery margin change (SEK)',
                path: ['learning', 'max_daily_param_change', 'battery_use_margin_sek'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.export_profit_margin_sek',
                label: 'Export margin change (SEK)',
                path: ['learning', 'max_daily_param_change', 'export_profit_margin_sek'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.future_price_guard_buffer_sek',
                label: 'Future guard buffer change (SEK)',
                path: ['learning', 'max_daily_param_change', 'future_price_guard_buffer_sek'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.load_safety_margin_percent',
                label: 'Load safety change (%)',
                path: ['learning', 'max_daily_param_change', 'load_safety_margin_percent'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.pv_confidence_percent',
                label: 'PV confidence change (%)',
                path: ['learning', 'max_daily_param_change', 'pv_confidence_percent'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.s_index_base_factor',
                label: 'S-index base change',
                path: ['learning', 'max_daily_param_change', 's_index_base_factor'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.s_index_pv_deficit_weight',
                label: 'S-index PV weight change',
                path: ['learning', 'max_daily_param_change', 's_index_pv_deficit_weight'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 'learning.max_daily_param_change.s_index_temp_weight',
                label: 'S-index temp weight change',
                path: ['learning', 'max_daily_param_change', 's_index_temp_weight'],
                type: 'number',
                isAdvanced: true,
            },
        ],
    },
    {
        title: 'S-Index Safety',
        description: 'Seasonal index parameters for reserve calculations.',
        fields: [
            {
                key: 's_index.temp_cold_c',
                label: 'Cold temp (°C)',
                path: ['s_index', 'temp_cold_c'],
                type: 'number',
                isAdvanced: true,
            },
            {
                key: 's_index.s_index_horizon_days',
                label: 'S-Index Horizon (days)',
                path: ['s_index', 's_index_horizon_days'],
                type: 'select',
                isAdvanced: true,
                options: [
                    { label: '1 Day', value: '1' },
                    { label: '2 Days', value: '2' },
                    { label: '3 Days', value: '3' },
                    { label: '4 Days', value: '4' },
                    { label: '5 Days', value: '5' },
                    { label: '6 Days', value: '6' },
                    { label: '7 Days', value: '7' },
                ],
            },
        ],
    },
]

export const uiSections: SettingsSection[] = [
    {
        title: 'Notifications',
        description: 'Configure automated notifications via Home Assistant.',
        fields: [
            {
                key: 'executor.notifications.service',
                label: 'HA Notify Service',
                helper: 'e.g. notify.mobile_app_iphone',
                path: ['executor', 'notifications', 'service'],
                type: 'service',
            },
            {
                key: 'executor.notifications.on_charge_start',
                label: 'On charge start',
                path: ['executor', 'notifications', 'on_charge_start'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_charge_stop',
                label: 'On charge stop',
                path: ['executor', 'notifications', 'on_charge_stop'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_export_start',
                label: 'On export start',
                path: ['executor', 'notifications', 'on_export_start'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_export_stop',
                label: 'On export stop',
                path: ['executor', 'notifications', 'on_export_stop'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_water_heat_start',
                label: 'On water heating start',
                path: ['executor', 'notifications', 'on_water_heat_start'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_water_heat_stop',
                label: 'On water heating stop',
                path: ['executor', 'notifications', 'on_water_heat_stop'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_soc_target_change',
                label: 'On SoC target change',
                path: ['executor', 'notifications', 'on_soc_target_change'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_override_activated',
                label: 'On override activated',
                path: ['executor', 'notifications', 'on_override_activated'],
                type: 'boolean',
            },
            {
                key: 'executor.notifications.on_error',
                label: 'On error',
                path: ['executor', 'notifications', 'on_error'],
                type: 'boolean',
            },
        ],
    },
    {
        title: 'Dashboard Defaults',
        description: 'Overlay defaults and refresh cadence for the planner dashboard.',
        fields: [
            {
                key: 'dashboard.auto_refresh_enabled',
                label: 'Auto refresh',
                helper: 'Enable automatic refresh of the dashboard schedule.',
                path: ['dashboard', 'auto_refresh_enabled'],
                type: 'boolean',
            },
        ],
    },
    {
        title: 'AI Advisor',
        description: 'Control the Smart Advisor LLM settings.',
        fields: [
            {
                key: 'advisor.enable_llm',
                label: 'Enable LLM advice',
                path: ['advisor', 'enable_llm'],
                type: 'boolean',
            },
            {
                key: 'advisor.auto_fetch',
                label: 'Auto-fetch advice on dashboard load',
                path: ['advisor', 'auto_fetch'],
                type: 'boolean',
            },
            {
                key: 'advisor.personality',
                label: 'Advisor personality',
                path: ['advisor', 'personality'],
                type: 'select',
                options: [
                    { label: 'Concise (Money focus)', value: 'concise' },
                    { label: 'Friendly (Emoji style)', value: 'friendly' },
                    { label: 'Technical (Data heavy)', value: 'technical' },
                ],
            },
        ],
    },
]

export const advancedSections: SettingsSection[] = [
    {
        title: 'Experimental Features',
        description: 'Toggle advanced and experimental modes.',
        fields: [
            {
                key: 'executor.interval_seconds',
                label: 'Executor Interval',
                helper: 'How often the executor runs to update inverter settings. Lower = faster response, higher = less resource usage.',
                path: ['executor', 'interval_seconds'],
                type: 'select',
                options: [
                    { label: '5 seconds', value: '5' },
                    { label: '10 seconds', value: '10' },
                    { label: '15 seconds', value: '15' },
                    { label: '20 seconds', value: '20' },
                    { label: '30 seconds', value: '30' },
                    { label: '1 minute', value: '60' },
                    { label: '2.5 minutes', value: '150' },
                    { label: '5 minutes', value: '300' },
                    { label: '10 minutes', value: '600' },
                ],
            },
            {
                key: 'automation.schedule.every_minutes',
                label: 'Planner Interval',
                helper: 'How often to regenerate the optimal schedule. Lower = faster SoC adaptation, higher = less CPU usage.',
                path: ['automation', 'schedule', 'every_minutes'],
                type: 'select',
                options: [
                    { label: '15 minutes', value: '15' },
                    { label: '30 minutes', value: '30' },
                    { label: '60 minutes', value: '60' },
                    { label: '90 minutes', value: '90' },
                ],
            },
            {
                key: 'automation.enable_scheduler',
                label: 'Enable Background Scheduler',
                helper: 'Master toggle for automatic schedule regeneration.',
                path: ['automation', 'enable_scheduler'],
                type: 'boolean',
            },

            {
                key: 'learning.auto_tune_enabled',
                label: 'Enable Auto-Tuning',
                helper: 'Automatically adjust system constants based on historical data.',
                path: ['learning', 'auto_tune_enabled'],
                type: 'boolean',
            },
            {
                key: 'learning.reflex_enabled',
                label: 'Enable Reflex Loop',
                helper: 'Real-time parameter adjustment loop.',
                path: ['learning', 'reflex_enabled'],
                type: 'boolean',
            },
            {
                key: 's_index.mode',
                label: 'S-Index Mode',
                helper: 'Switch between probabilistic risk and dynamic balancing.',
                path: ['s_index', 'mode'],
                type: 'select',
                options: [
                    { label: 'Probabilistic (P10/P90)', value: 'probabilistic' },
                    { label: 'Dynamic (Adaptive)', value: 'dynamic' },
                ],
                showIf: {
                    configKey: 'system.has_battery',
                    value: true,
                    disabledText: "Enable 'Home battery installed' in System Profile to configure",
                },
            },
        ],
    },
    {
        title: 'Inverter Logic',
        description: 'Custom command strings for your inverter work modes.',
        fields: [
            {
                key: 'executor.inverter.work_mode_export',
                label: 'Export Mode String',
                helper: 'The exact value your inverter select entity expects for Export mode.',
                path: ['executor', 'inverter', 'work_mode_export'],
                type: 'text',
                showIf: {
                    configKey: 'system.inverter_profile',
                    value: 'generic',
                },
            },
            {
                key: 'executor.inverter.work_mode_zero_export',
                label: 'Zero-Export Mode String',
                helper: 'The exact value your inverter select entity expects for Zero-Export mode.',
                path: ['executor', 'inverter', 'work_mode_zero_export'],
                type: 'text',
                showIf: {
                    configKey: 'system.inverter_profile',
                    value: 'generic',
                },
            },
        ],
    },
    {
        title: 'Danger Zone',
        description: 'Sensitive actions. Proceed with caution.',
        fields: [], // Handled specially in render
    },
]

export const systemFieldList = systemSections.flatMap((section) => section.fields)
export const parameterFieldList = parameterSections.flatMap((section) => section.fields)
export const uiFieldList = uiSections.flatMap((section) => section.fields)
export const advancedFieldList = advancedSections.flatMap((section) => section.fields)

// DEBUG: Log battery_soc field definition on module load
const batterySocField = systemFieldList.find((f) => f.key === 'input_sensors.battery_soc')
if (batterySocField) {
    console.warn('[SETTINGS_DEBUG] Module loaded - battery_soc field definition:', {
        key: batterySocField.key,
        type: batterySocField.type,
        label: batterySocField.label,
        path: batterySocField.path,
    })
} else {
    console.error('[SETTINGS_DEBUG] ERROR: battery_soc field not found in systemFieldList!')
}

export const allFields = [
    ...systemFieldList,
    ...parameterFieldList,
    ...uiFieldList,
    ...advancedFieldList,
    {
        key: 'dashboard.overlay_defaults',
        label: 'Overlay Defaults',
        path: ['dashboard', 'overlay_defaults'],
        type: 'text' as FieldType,
    },
]

export const fieldMap = allFields.reduce(
    (acc, field) => {
        acc[field.key] = field
        return acc
    },
    {} as Record<string, BaseField>,
)
