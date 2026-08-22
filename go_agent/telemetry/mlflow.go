// Package telemetry provides MLflow and OpenTelemetry tracing integrations for Google ADK in Go (adk-go).
package telemetry

import (
	"context"
	"fmt"
	"log"
	"os"

	"go.opentelemetry.io/otel"
	"go.opentelemetry.io/otel/exporters/otlp/otlptrace/otlptracehttp"
	"go.opentelemetry.io/otel/sdk/resource"
	sdktrace "go.opentelemetry.io/otel/sdk/trace"
	semconv "go.opentelemetry.io/otel/semconv/v1.26.0"
)

// MLflowConfig holds configuration for the MLflow Tracing and Gateway integration.
type MLflowConfig struct {
	TrackingURI    string // e.g. "http://localhost:5000"
	ExperimentName string // e.g. "adk-go-bookforge"
	ServiceName    string // e.g. "adk-go-agent"
}

// InitMLflowTracing sets up OpenTelemetry OTLP HTTP trace exporter pointing to MLflow tracking server.
func InitMLflowTracing(ctx context.Context, cfg MLflowConfig) (*sdktrace.TracerProvider, func(context.Context) error, error) {
	if cfg.TrackingURI == "" {
		cfg.TrackingURI = "http://localhost:5000"
	}
	if cfg.ServiceName == "" {
		cfg.ServiceName = "adk-go-agent"
	}

	// MLflow OTLP ingestion endpoint
	endpoint := fmt.Sprintf("%s/v1/traces", cfg.TrackingURI)

	// Create OTLP HTTP trace exporter
	exporter, err := otlptracehttp.New(ctx,
		otlptracehttp.WithEndpointURL(endpoint),
		otlptracehttp.WithInsecure(),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create OTLP trace exporter: %w", err)
	}

	// Create resource attributes
	res, err := resource.New(ctx,
		resource.WithAttributes(
			semconv.ServiceNameKey.String(cfg.ServiceName),
			semconv.ServiceVersionKey.String("1.0.0"),
		),
	)
	if err != nil {
		return nil, nil, fmt.Errorf("failed to create resource: %w", err)
	}

	// Configure global TracerProvider
	tp := sdktrace.NewTracerProvider(
		sdktrace.WithBatcher(exporter),
		sdktrace.WithResource(res),
	)
	otel.SetTracerProvider(tp)

	log.Printf("[ADK-GO] MLflow OpenTelemetry tracing initialized at %s", endpoint)

	shutdown := func(ctx context.Context) error {
		return tp.Shutdown(ctx)
	}

	return tp, shutdown, nil
}

// GetMLflowGatewayEndpoint returns the AI Gateway endpoint for adk-go model connectors.
func GetMLflowGatewayEndpoint(gatewayBaseURL, routeName string) string {
	if gatewayBaseURL == "" {
		gatewayBaseURL = "http://localhost:5000/v1"
	}
	return fmt.Sprintf("%s/endpoints/%s/invocations", gatewayBaseURL, routeName)
}
