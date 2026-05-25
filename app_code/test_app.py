import os
import pytest
import boto3
from io import BytesIO
from moto import mock_aws

# 1. Set up fake AWS credentials and Environment Variables BEFORE importing the app
os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
os.environ['AWS_SECURITY_TOKEN'] = 'testing'
os.environ['AWS_SESSION_TOKEN'] = 'testing'
os.environ['AWS_DEFAULT_REGION'] = 'eu-west-1'
os.environ['DYNAMODB_TABLE'] = 'prima-test-db'
os.environ['S3_BUCKET_NAME'] = 'prima-test-bucket'

@pytest.fixture
def mock_aws_services():
    """Spins up fake AWS services in memory."""
    with mock_aws():
        # Fake DynamoDB
        dynamodb = boto3.resource('dynamodb', region_name='eu-west-1')
        dynamodb.create_table(
            TableName='prima-test-db',
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            BillingMode='PAY_PER_REQUEST'
        )
        
        # Fake S3
        s3 = boto3.client('s3', region_name='eu-west-1')
        s3.create_bucket(
            Bucket='prima-test-bucket',
            CreateBucketConfiguration={'LocationConstraint': 'eu-west-1'}
        )
        yield

@pytest.fixture
def client(mock_aws_services):
    """Creates a mock Flask client connected to the fake AWS services."""
    from app import app
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# ---------------------------------------------------
# Unit Tests
# ---------------------------------------------------

def test_health_check(client):
    """Test that the Kubernetes health probe endpoint works."""
    response = client.get('/health')
    assert response.status_code == 200
    assert response.get_json() == {"status": "healthy"}

def test_create_user(client):
    """Test that a user can be created and an image uploaded to mock S3."""
    # Simulate a file upload
    data = {
        'name': 'Test User',
        'email': 'test@example.com',
        'password': 'supersecurepassword',
        'image': (BytesIO(b"fake image data"), 'avatar.jpg')
    }
    
    response = client.post('/users', data=data, content_type='multipart/form-data')
    
    assert response.status_code == 201
    json_data = response.get_json()
    assert 'id' in json_data
    assert json_data['message'] == "User created successfully"
    assert "prima-test-bucket" in json_data['avatar_url']

def test_get_users(client):
    """Test that we can retrieve users without leaking passwords."""
    # 1. Insert a dummy user
    data = {
        'name': 'Secure User',
        'email': 'secure@example.com',
        'password': 'hiddenpassword',
        'image': (BytesIO(b"fake image data"), 'avatar.jpg')
    }
    client.post('/users', data=data, content_type='multipart/form-data')
    
    # 2. Fetch all users
    response = client.get('/users')
    assert response.status_code == 200
    
    # 3. Parse the dictionary response
    json_data = response.get_json()
    
    # Check that the API returned our 'count' and 'users' keys
    assert 'count' in json_data
    assert 'users' in json_data
    assert json_data['count'] == 1
    
    # 4. Check the actual user list inside the dictionary
    user_list = json_data['users']
    assert len(user_list) == 1
    assert user_list[0]['name'] == 'Secure User'
    assert 'password_hash' not in user_list[0] # Ensure security!