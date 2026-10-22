const express = require("express");
const { ApolloServer } = require("apollo-server-express");
const { ApolloServerPluginLandingPageDisabled } = require("apollo-server-core");
const { readFileSync } = require("fs");
const path = require("path");
const cors = require("cors");
const resolvers = require("./resolvers");
const { authenticateToken } = require("./db");

const typeDefs = readFileSync(path.join(__dirname, "schema.graphql"), "utf-8");

async function start() {
  const app = express();
  app.use(cors());

  app.use((req, res, next) => {
    const authHeader = req.headers.authorization || "";
    if (authHeader.startsWith("Bearer ")) {
      req.user = authenticateToken(authHeader.slice(7));
    } else {
      req.user = null;
    }
    next();
  });

  const server = new ApolloServer({
    typeDefs,
    resolvers,
    introspection: true, 
    plugins: [ApolloServerPluginLandingPageDisabled()],
    context: ({ req }) => ({ user: req.user }),
  });

  await server.start();
  server.applyMiddleware({ app, path: "/graphql" });

  const frontendPath = path.join(__dirname, "..", "frontend");
  app.use(express.static(frontendPath));
  app.get("/", (req, res) => {
    res.sendFile(path.join(frontendPath, "index.html"));
  });

  const PORT = process.env.PORT || 4000;
  app.listen(PORT, () => {
    console.log(`\nAstraeus Aerospace API online on port ${PORT}\n`);
  });
}

start();
