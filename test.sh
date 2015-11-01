#!/bin/bash

export DJANGO_SETTINGS_MODULE=sikteeri.settings
export SIKTEERI_CONFIGURATION=dev

py.test --cov=membership --cov=sikteeri --cov=services
