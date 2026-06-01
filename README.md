# Aussie EcoLens

A multi-cloud serverless wildlife observation platform built for FIT5225.

## Live Demo
https://aussie-ecolens-sk5r2fjkn-mavishrx-15s-projects.vercel.app

## Tech Stack

### AWS
- Cognito — User authentication
- S3 — File and thumbnail storage
- Lambda — Serverless processing (upload, ML inference, tagging)
- API Gateway — RESTful API endpoints
- DynamoDB — Metadata and tag storage
- SNS — Email notifications

### GCP
- Cloud Run — Real-time wildlife statistics dashboard
- Firestore — Secondary data storage

### Frontend
- React + Vite + Ant Design

### Backend
- Python (Lambda functions)

## Project Structure
frontend/     # React frontend
backend/      # Lambda functions and query API
database/     # Firestore schema and sync scripts
docs/         # Reports and architecture diagrams

## Features
- User registration and login with email verification
- Image and video upload with SHA-256 deduplication
- Automatic wildlife species detection using ML model
- Thumbnail generation for images and videos
- Multi-mode search: by tags, species, thumbnail URL, or file
- Manual tag add/remove and file deletion
- Email notifications for species detections via SNS
- Real-time statistics dashboard powered by GCP Cloud Run