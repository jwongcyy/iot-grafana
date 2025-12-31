msg.measurement = "tss_rs485";          // REQUIRED: Measurement name
msg.payload = {                         // REQUIRED: Field values
    tss_value: msg.payload[0],
    unit: "tbd"
};
msg.tags = {                            // OPTIONAL: Tags
    location: "spirulina",
    sensor: "TSS_1",
    source: "modbus"
};
// timestamp is optional

return msg;
