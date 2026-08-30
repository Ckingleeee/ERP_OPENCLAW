const databaseName = process.env.MONGODB_APP_DATABASE;
const username = process.env.MONGODB_APP_USER;
const password = process.env.MONGODB_APP_PASSWORD;

if (!databaseName || !username || !password) {
  throw new Error("MongoDB application user environment is incomplete");
}

const applicationDatabase = db.getSiblingDB(databaseName);
applicationDatabase.createUser({
  user: username,
  pwd: password,
  roles: [{ role: "readWrite", db: databaseName }],
});
