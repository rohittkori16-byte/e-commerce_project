/**
 * MongoDB Single-Node Replica Set Initialization Script
 * Used by Docker Compose or local setup to enable multi-document transactions.
 */
try {
  var status = rs.status();
  print("Replica set is already initialized: " + status.set);
} catch (e) {
  print("Initializing single-node replica set rs0...");
  var config = {
    _id: "rs0",
    members: [
      { _id: 0, host: "mongo:27017" }
    ]
  };
  var result = rs.initiate(config);
  printjson(result);
}

