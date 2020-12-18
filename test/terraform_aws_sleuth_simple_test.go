package test

import (
	"testing"
	"time"

	awssdk "github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/gruntwork-io/terratest/modules/aws"
	"github.com/gruntwork-io/terratest/modules/terraform"
	test_structure "github.com/gruntwork-io/terratest/modules/test-structure"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func GetLambdaEnvars(t *testing.T, region string) (envars map[string]*string, err error) {
	client := aws.NewLambdaClient(t, region)

	input := &lambda.GetFunctionConfigurationInput{
		FunctionName: awssdk.String("iam-sleuth-test"),
		Qualifier:    awssdk.String("$LATEST"),
	}

	result, err := client.GetFunctionConfiguration(input)
	return result.Environment.Variables, err
}

func TestTerraformSimpleSanityCheck(t *testing.T) {

	tempTestFolder := test_structure.CopyTerraformFolderToTemp(t, "../", "examples/simple")
	awsRegion := "us-east-2"

	terraformOptions := &terraform.Options{
		TerraformDir: tempTestFolder,
		Vars:         map[string]interface{}{},
		EnvVars: map[string]string{
			"AWS_DEFAULT_REGION": awsRegion,
			"AWS_REGION":         awsRegion,
		},
	}

	defer terraform.Destroy(t, terraformOptions)
	terraform.InitAndApply(t, terraformOptions)

	// Sleep here to let AWS update or will get no access to KMS error
	time.Sleep(5 * time.Second)

	// lets try to invoke the lambda to ensure proper setup
	_, err := aws.InvokeFunctionE(t, awsRegion, "iam-sleuth-test", FunctionPayload{ShouldFail: false, Echo: "hi!"})

	// Function-specific errors have their own special return, should be nil
	functionError, ok := err.(*aws.FunctionError)
	require.False(t, ok)
	assert.Equal(t, (*aws.FunctionError)(nil), functionError)

	// check envars
	resp, err := GetLambdaEnvars(t, awsRegion)
	assert.Equal(t, *resp["MSG_TEXT"], "Please run key rotation tool!")
	assert.Equal(t, *resp["MSG_TITLE"], "Key Rotation Instructions")
	assert.Equal(t, *resp["ENABLE_AUTO_EXPIRE"], "false")
	assert.Equal(t, *resp["WARNING_AGE"], "85")
	assert.Equal(t, *resp["EXPIRATION_AGE"], "90")
}

type FunctionPayload struct {
	Echo       string
	ShouldFail bool
}
