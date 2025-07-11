const express = require('express')
const path = require('path')
const app = express()
const port = 3000

app.use(express.static(path.join(__dirname, 'src')))

app.get('/:user_name/:game_name', (req, res) => {
  res.sendFile(path.join(__dirname, 'src', 'index.html'))
})

app.listen(port, '0.0.0.0', () => {
  console.log(`Example app listening on port ${port}`)
})