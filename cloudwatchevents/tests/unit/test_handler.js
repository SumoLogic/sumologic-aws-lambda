'use strict';

const app = require('../../app.js');
const chai = require('chai');
const expect = chai.expect;
var event, context;


describe('Tests index', function () {
    var env;

    // mocking an environment
    before(function () {
        env = process.env;
        process.env = { SUMO_ENDPOINT:"https://nite-events.sumologic.net/receiver/v1/http/ZaVnC4dhaV3_T1vGzqOZIeERyqOzOE1e6RjXE59PErnOkZ-PSjb6gGesLBli8dzUvQWzDhRHRhYByGLHWYOlkss6S-vBXYOf7RDk41o2fiVC08g6ogm1dA==" };
    });

    it('verifies successful response', async () => {
        const result = await app.lambdaHandler(event, context, (err, result) => {
            expect(result).to.be.an('object');
            expect(result.statusCode).to.equal(200);
            expect(result.body).to.be.an('string');

            let response = JSON.parse(result.body);

            expect(response).to.be.an('object');
            expect(response.message).to.be.equal("Success");
            expect(response.location).to.be.an("string");
        });
    });

    // restoring everything back
    after(function () {
        process.env = env;
    });
});

