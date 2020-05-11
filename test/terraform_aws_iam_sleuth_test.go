package test

import (
	"testing"

	"github.com/gruntwork-io/terratest/modules/terraform"
	test_structure "github.com/gruntwork-io/terratest/modules/test-structure"
)

func TestTerraformAwsIamSleuthWithSnsTopic(t *testing.T) {
	t.Parallel()

	tempTestFolder := test_structure.CopyTerraformFolderToTemp(t, "../", "examples/simple")
	awsRegion := "us-west-2"

	terraformOptions := &terraform.Options{
		// The path to where our Terraform code is located
		TerraformDir: tempTestFolder,
		// Environment variables to set when running Terraform
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
		},
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)
}
