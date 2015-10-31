#!/bin/bash

export DJANGO_SETTINGS_MODULE=sikteeri.settings
export SIKTEERI_CONFIG=dev

py.test --cov-config .coveragerc --cov=membership --cov=sikteeri --cov=services
