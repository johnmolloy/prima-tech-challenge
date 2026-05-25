import os
import uuid
from flask import Flask, request, jsonify
import boto3
from werkzeug.security import generate_password_hash
from werkzeug.utils import secure_filename

app = Flask(__name__)

region = os.getenv('AWS_REGION', 'eu-west-1')

dynamodb = boto3.resource('dynamodb', region_name=region)
s3_client = boto3.client('s3', region_name=region)

table_name = os.getenv('DYNAMODB_TABLE', 'prima-user-db')
table = dynamodb.Table(table_name)
s3_bucket = os.getenv('S3_BUCKET_NAME')

@app.route('/')
def hello_world():
    return "Hello John"

@app.route('/users', methods=['POST'])
def create_user():
    # 1. Validate that an image file is attached
    if 'image' not in request.files:
        return jsonify({"error": "No image file provided"}), 400
    
    image_file = request.files['image']
    if image_file.filename == '':
        return jsonify({"error": "Empty image filename"}), 400

    # 2. Extract text fields from the form data (not JSON anymore)
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    username = request.form.get('username')
    password = request.form.get('password')

    if not all([first_name, last_name, username, password]):
        return jsonify({"error": "Missing required text fields"}), 400

    user_id = str(uuid.uuid4())
    hashed_password = generate_password_hash(password)

    # 3. Secure the filename and construct the S3 Object Key
    safe_filename = secure_filename(image_file.filename)
    s3_key = f"profile_images/{user_id}/{safe_filename}"

    try:
        # 4. Upload the file directly to S3
        s3_client.upload_fileobj(
            image_file, 
            s3_bucket, 
            s3_key,
            # Optional: Add metadata or content types if needed
            ExtraArgs={"ContentType": image_file.content_type}
        )

        # 5. Write the user data AND the S3 reference to DynamoDB
        table.put_item(
            Item={
                'id': user_id,
                'first_name': first_name,
                'last_name': last_name,
                'username': username,
                'password_hash': hashed_password,
                'profile_image_key': s3_key # Store where to find the image
            }
        )
        
        return jsonify({
            "message": "User and image created successfully",
            "id": user_id,
            "image_location": s3_key
        }), 201

    except Exception as e:
        print(f"Server error: {str(e)}")
        return jsonify({"error": "Failed to process user creation"}), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)