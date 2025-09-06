import Redis from "ioredis";
import crypto from "crypto";
export class SessionManager {
    static SESSIONS_KEY = 'sessions';

    constructor(endpoint) {
        this.endpoint = endpoint;
        this.redis = new Redis(endpoint);
    }

    async createSession(userId, gameId) {
        let sessionId = crypto.randomUUID();
        let sessionData = {
            sessionId,
            userId,
            gameId
        };
        await this.redis.lpush(SessionManager.SESSIONS_KEY, JSON.stringify(sessionData));

        console.log(`Attempting to create session: ${JSON.stringify(sessionData)}`);

        // either wait for an ack or timeout
        let ack = await this.redis.blpop(sessionId, 60);

        if (!ack) {
            throw new Error("Session creation timed out");
        }

        console.log(`Received ack: ${ack[1]}`);
        ack = JSON.parse(ack[1]);
        console.log(`Session created: ${JSON.stringify(ack)}`);

        return ack;
    }
}