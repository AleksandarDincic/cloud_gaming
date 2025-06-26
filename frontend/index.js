const express = require('express')
const app = express()
const port = 3000

app.get('/:user_name/:game_name', (req, res) => {
  let params = {
    user_name: req.params.user_name,
    game_name: req.params.game_name
  }
  res.send(`NOW SERVING GAME ${params.game_name} FOR USER ${params.user_name}`)
})

app.listen(port, () => {
  console.log(`Example app listening on port ${port}`)
})