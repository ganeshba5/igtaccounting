# Architecture Comparison: Two-Server vs Single-Server

## Why Two Servers?

### Current Two-Server Architecture

```
┌─────────────────┐         ┌─────────────────┐
│   Frontend      │         │    Backend       │
│   (Vite Dev)    │ ──────> │   (Flask API)    │
│   Port 3000     │         │   Port 5001      │
└─────────────────┘         └─────────────────┘
     React App                    Python API
```

### Why This Exists

1. **Development Experience**
   - Vite provides Hot Module Replacement (HMR)
   - Changes appear instantly without full page reload
   - Fast refresh for React components
   - Better debugging tools

2. **Separation of Concerns**
   - Frontend and backend are independent
   - Can develop/deploy separately
   - Frontend can be deployed to CDN
   - Backend can scale independently

3. **Technology Stack**
   - Frontend: React + Vite (JavaScript ecosystem)
   - Backend: Flask (Python ecosystem)
   - Different build tools and processes

## Single-Server Architecture

```
┌─────────────────────────────────┐
│      Flask Server               │
│      Port 5001                  │
│                                 │
│  ┌──────────┐  ┌─────────────┐ │
│  │   API    │  │  Static     │ │
│  │  Routes  │  │  Frontend   │ │
│  │  /api/*  │  │  /*         │ │
│  └──────────┘  └─────────────┘ │
└─────────────────────────────────┘
```

### How It Works

1. Build frontend: `npm run build` → creates `frontend/dist/`
2. Flask serves static files from `frontend/dist/`
3. All routes except `/api/*` serve the React app
4. React Router handles client-side routing

## Comparison

| Feature | Two-Server (Dev) | Single-Server (Prod) |
|---------|-----------------|---------------------|
| **Hot Reload** | ✅ Yes | ❌ No (must rebuild) |
| **Development Speed** | ✅ Fast | ⚠️ Slower |
| **Deployment Complexity** | ⚠️ Two processes | ✅ One process |
| **Port Management** | ⚠️ Two ports | ✅ One port |
| **Resource Usage** | ⚠️ Higher | ✅ Lower |
| **Production Ready** | ⚠️ Not ideal | ✅ Yes |
| **LAN Access** | ⚠️ Two URLs | ✅ One URL |

## When to Use Each

### Use Two-Server Mode When:
- ✅ Actively developing
- ✅ Making frequent frontend changes
- ✅ Need hot reload
- ✅ Debugging frontend/backend separately

### Use Single-Server Mode When:
- ✅ Deploying to production
- ✅ Simple deployment needed
- ✅ Running on a single machine
- ✅ Sharing with others (simpler setup)

## Migration Path

The application supports both modes seamlessly:

1. **Development**: Use two-server mode
   ```bash
   ./start_backend.sh    # Terminal 1
   ./start_frontend.sh   # Terminal 2
   ```

2. **Production**: Use single-server mode
   ```bash
   ./start_single_server.sh
   ```

3. **Switch Anytime**: No code changes needed!

## Technical Details

### Two-Server Mode
- Frontend: Vite dev server with proxy to Flask
- Backend: Flask with CORS enabled
- API calls: Frontend → `http://localhost:5001/api/*`

### Single-Server Mode
- Frontend: Built static files in `frontend/dist/`
- Backend: Flask serves static files + API
- API calls: Frontend → `/api/*` (same origin)
- React Router: All non-API routes serve `index.html`

## Performance Considerations

### Two-Server (Development)
- **Memory**: ~200-300MB (Vite + Flask)
- **CPU**: Higher (dev server overhead)
- **Network**: Two connections

### Single-Server (Production)
- **Memory**: ~100-150MB (Flask only)
- **CPU**: Lower (no dev server)
- **Network**: One connection
- **Build Size**: Optimized production bundle

## Conclusion

**Best Practice:**
- **Develop**: Two-server mode for better DX
- **Deploy**: Single-server mode for simplicity

The application is designed to support both modes, so you can choose based on your needs!

