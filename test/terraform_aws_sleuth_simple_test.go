package test

import (
	"os"
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

	github_release := os.Getenv("RELEASE_TAG")
	validation_sha := os.Getenv("VALIDATION_SHA")

	terraformOptions := &terraform.Options{
		TerraformDir: tempTestFolder,
		Vars: map[string]interface{}{
			"github_release": github_release,
			"validation_sha": validation_sha,
		},
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

	// Sleep here to let all the lambda logs in flight write to log group.
	// Failing to sleep here will recreate the log group after tf destroy
	time.Sleep(60 * time.Second)

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
	assert.Equal(t, *resp["INACTIVITY_AGE"], "30")
	assert.Equal(t, *resp["INACTIVITY_WARNING_AGE"], "20")
}

type FunctionPayload struct {
	Echo       string
	ShouldFail bool
}
