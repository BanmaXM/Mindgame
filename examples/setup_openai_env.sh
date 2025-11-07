#!/bin/bash

# This script sets up the environment variables needed for OpenAI API access
# Usage: source setup_openai_env.sh [azure|openai]

# Default to standard OpenAI if not specified
API_TYPE=${1:-openai}

if [ "$API_TYPE" = "azure" ]; then
    echo "Setting up environment for Azure OpenAI API"
    export OPENAI_API_TYPE="azure_key"
    
    # Prompt for Azure OpenAI endpoint if not set
    if [ -z "$OPENAI_BASE_URL" ]; then
        read -p "Enter your Azure OpenAI endpoint (e.g., https://your-resource.openai.azure.com): " azure_endpoint
        export OPENAI_BASE_URL="$azure_endpoint"
    fi
    
    # Prompt for Azure OpenAI API key if not set
    if [ -z "$OPENAI_API_KEY" ]; then
        read -sp "Enter your Azure OpenAI API key: " api_key
        echo ""  # Add a newline after the hidden input
        export OPENAI_API_KEY="$api_key"
    fi
    
    # Set a default Azure deployment name
    if [ -z "$OPENAI_MODEL" ]; then
        read -p "Enter your Azure OpenAI deployment name: " deployment_name
        export OPENAI_MODEL="$deployment_name"
    fi
    
    echo "Azure OpenAI configuration:"
    echo "- API Type: Azure OpenAI"
    echo "- Endpoint: $OPENAI_BASE_URL"
    echo "- Model/Deployment: $OPENAI_MODEL"
    echo "- API Key: [HIDDEN]"
else
    echo "Setting up environment for standard OpenAI API"
    unset OPENAI_API_TYPE
    
    # Prompt for OpenAI API key if not set
    if [ -z "$OPENAI_API_KEY" ]; then
        read -sp "Enter your OpenAI API key: " api_key
        echo ""  # Add a newline after the hidden input
        export OPENAI_API_KEY="$api_key"
    fi
    
    # Set default OpenAI model
    if [ -z "$OPENAI_MODEL" ]; then
        export OPENAI_MODEL="gpt-4o"
    fi
    
    # Set default OpenAI base URL
    if [ -z "$OPENAI_BASE_URL" ]; then
        export OPENAI_BASE_URL="https://api.openai.com/v1"
    fi
    
    echo "Standard OpenAI configuration:"
    echo "- API Type: Standard OpenAI"
    echo "- Base URL: $OPENAI_BASE_URL"
    echo "- Model: $OPENAI_MODEL"
    echo "- API Key: [HIDDEN]"
fi

echo ""
echo "Environment variables have been set. You can now run the game using:"
echo "bash examples/run_game.sh cli"
echo "or"
echo "bash examples/run_game.sh web"
