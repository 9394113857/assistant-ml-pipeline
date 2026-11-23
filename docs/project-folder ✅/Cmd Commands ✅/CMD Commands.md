Sure bro! 🫡 Run this **direct API command** in Postman or your terminal and share the live response.

**GET – Training Review Queue**

```
https://assistant-service-g24j.onrender.com/api/v1/assistant/training/review-queue?status=pending
```

**Windows CMD (cURL):**

```
curl -X GET "https://assistant-service-g24j.onrender.com/api/v1/assistant/training/review-queue?status=pending" -H "Authorization: Bearer YOUR_ADMIN_JWT_TOKEN" -H "Content-Type: application/json"
```

Replace `YOUR_ADMIN_JWT_TOKEN` with your Admin JWT.

Share the complete response (you can mask the token). We'll check whether the API returns only ID 181 or also includes the 180 existing labelled records.
