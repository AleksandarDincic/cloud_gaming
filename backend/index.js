const express = require('express')
const path = require('path')
const cors = require('cors');
const session = require('./src/session.js');
const app = express()
const port = 3001

const redisEndpoint = 'redis://localhost:6379';
const sessionManager = new session.SessionManager(redisEndpoint);

app.use(express.static(path.join(__dirname, 'src')))
app.use(cors())

app.get('/create_session', async (req, res) => {
  let userId = req.query.user;
  let gameId = req.query.game;

  if (!userId || !gameId) {
    return res.status(400).json({ error: 'Missing user or game' });
  }

  try {
    let sessionInfo = await sessionManager.createSession(userId, gameId);
    res.json(sessionInfo);
  } catch (error) {
    console.error('Error creating session:', error);
    res.status(400).json({ error: `Failed to create session: ${error.message}` });
  }
});

app.listen(port, '0.0.0.0', () => {
  console.log(`Cloud Gaming backend listening on port ${port}`)
})