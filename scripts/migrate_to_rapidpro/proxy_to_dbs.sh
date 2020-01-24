#!/bin/bash
ssh -CN prd-unicore-worker01.za.prk-host.net -L localhost:7000:10.1.1.204:5432
