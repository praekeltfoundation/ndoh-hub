# ndoh-hub
NDOH Registration and Change service for MomConnect and NurseConnect

## Registration Information

// PMTCT

    // pmtct prebirth
    data: {
        "reg_type": "pmtct_prebirth",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "language": "eng_ZA",  // chosen message language
            "mom_dob": "1954-05-29",  // mother's date of birth
            "edd": "2016-09-07"  // estimated due date
        }
    }

    // pmtct postbirth
    data: {
        "reg_type": "pmtct_postbirth",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "language": "eng_ZA",  // chosen message language
            "mom_dob": "1954-05-29",  // mother's date of birth
            "baby_dob": "2015-11-11"  // baby's date of birth
        }
    }

// NURSECONNECT

    // nurseconnect
    data: {
        "reg_type": "nurseconnect",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "msisdn_registrant": "+27821235555",  // msisdn of the registrant
            "msisdn_device": "+27821234444",  // device msisdn
            "faccode": "123456",  // facility code
            "language": "eng_ZA",  // currently always eng_ZA for nurseconnect
        }
    }

// MOMCONNECT

    // momconnect_prebirth - clinic
    data: {
        "reg_type": "momconnect_prebirth",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "msisdn_registrant": "+27821235555",  // msisdn of the registrant
            "msisdn_device": "+27821234444",  // device msisdn
            "id_type": "sa_id",  // 'sa_id' | 'passport' | 'none'

            // if id_type == sa_id, then
            "sa_id_no": "8108015001051",
            "mom_dob": "1982-08-01"
            // if id_type == passport, then
            "passport_no": "abc1234",
            "passport_origin": "bw",
            // if id_type == none, then
            "mom_dob": "1982-08-03",

            "language": "eng_ZA",
            "edd": "2016-01-01",  // estimated due date
            "faccode": "123456",  // facility/clinic code
            "consent": true,  // or null
        }
    }

    // momconnect_prebirth - chw
    data: {
        "reg_type": "momconnect_prebirth",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "msisdn_registrant": "+27821235555",  // msisdn of the registrant
            "msisdn_device": "+27821234444",  // device msisdn
            "id_type": "sa_id",  // 'sa_id' | 'passport' | 'none'

            // if id_type == sa_id, then
            "sa_id_no": "8108015001051",
            "mom_dob": "1982-08-01"
            // if id_type == passport, then
            "passport_no": "abc1234",
            "passport_origin": "bw",
            // if id_type == none, then
            "mom_dob": "1982-08-03",

            "language": "eng_ZA",
            "consent": true,  // or null
        }
    }

    // momconnect_prebirth - public
    data: {
        "reg_type": "momconnect_prebirth",
        "registrant_id": "cb245673-aa41-4302-ac47-00000000007",  // identity id
        "data": {
            "operator_id": "cb245673-aa41-4302-ac47-00000000007",  // device owner id
            "msisdn_registrant": "+27821235555",  // msisdn of the registrant
            "msisdn_device": "+27821235555",  // device msisdn
            "language": "eng_ZA",
            "consent": true,  // or null
        }
    }

## Change Information

// PMTCT

    // pmtct optout loss (no loss messages)
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-10000000001",
        "action": "pmtct_loss_optout",
        "data": {
            "reason": "miscarriage"  // | "babyloss" | "stillbirth"
        }
    }

    // pmtct optout nonloss
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-00000000001",
        "action": "pmtct_nonloss_optout",
        "data": {
            "reason": "unknown"  // | "not_useful" | "not_hiv_pos" | "other"
        }
    }

    // pmtct switch to loss messages
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-10000000001",
        "action": "pmtct_loss_switch",
        "data": {
            "reason": "miscarriage"
        }
    }

// BABY SWITCH

    // baby switch
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-10000000001",
        "action": "baby_switch",
        "data": {}
    }

// NURSECONNECT

    // nurseconnect change detail: faccode
    data: {
        "registrant_id": "uuid",
        "action": "nurse_update_detail",
        "data": {
            "faccode": "234567"
        }
    }

    // nurseconnect change detail: sa_id
    data: {
        "registrant_id": "uuid",
        "action": "nurse_update_detail",
        "data": {
            "id_type": "sa_id",
            "sa_id_no": "8108015001051",
            "dob": "1982-08-01"
        }
    }

    // nurseconnect change detail: passport
    data: {
        "registrant_id": "uuid",
        "action": "nurse_update_detail",
        "data": {
            "id_type": "passport",
            "passport_no": "abc1234",
            "passport_origin": "bw",
            "dob": "1982-08-02"
        }
    }

    // nurseconnect change detail: sanc number
    data: {
        "registrant_id": "uuid",
        "action": "nurse_update_detail",
        "data": {
            "sanc_no": "sanc_number"
        }
    }

    // nurseconnect change detail: persal number
    data: {
        "registrant_id": "uuid",
        "action": "nurse_update_detail",
        "data": {
            "persal_no": "persal_number"
        }
    }

    // nurseconnect change phone number
    data: {
        "registrant_id": "uuid",  // the new number's identity_id
        "action": "nurse_change_msisdn",
        "data": {
            "msisdn_old": "0825551001",
            "msisdn_new": "0825551002",
            // number of device used - will be the same as either msisdn_old or msisdn_new,
            // depending on whether number dialing in was recognised or not
            "msisdn_device": "0825555101"
        }
    }

    // nurseconnect optout
    data: {
        "registrant_id": "uuid",
        "action": "nurse_optout",
        "data": {
            "reason": "optout reason"
        }
    }

// MOMCONNECT

    // momconnect optout loss (no loss messages)
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-10000000001",
        "action": "momconnect_loss_optout",
        "data": {
            "reason": "miscarriage"  // | "babyloss" | "stillbirth"
        }
    }

    // momconnect optout nonloss
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-00000000001",
        "action": "momconnect_nonloss_optout",
        "data": {
            "reason": "unknown"  // | "other" | "not_useful"
        }
    }

    // momconnect switch to loss messages
    data: {
        "registrant_id": "cb245673-aa41-4302-ac47-10000000001",
        "action": "momconnect_loss_switch",
        "data": {
            "reason": "miscarriage"
        }
    }
