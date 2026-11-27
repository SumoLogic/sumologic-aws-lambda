// Unit tests with the AWS SDK mocked, no AWS access needed. Run with: npm test
const test = require("node:test");
const assert = require("node:assert");
const Module = require("module");
const path = require("path");

const DEST = "arn:aws:lambda:us-east-1:111111111111:function:sumo-forwarder";
const ctx = {invokedFunctionArn: "arn:aws:lambda:us-east-1:111111111111:function:connector", functionName: "connector"};

// State the mocked CloudWatch Logs client works from, reset per test.
let state;
function reset(overrides = {}) {
    state = Object.assign({
        tags: {},                 // current tags of every log group
        tagsError: null,          // error thrown by ListTagsLogGroup
        filters: [],              // subscription filters returned by DescribeSubscriptionFilters
        deleteErrors: [],         // errors thrown (once each) by DeleteSubscriptionFilter
        calls: {put: [], del: [], describe: [], tags: []},
    }, overrides);
}

class Cmd { constructor(input) { this.input = input; this.name = this.constructor.name; } }
const mocks = {
    "@aws-sdk/client-cloudwatch-logs": {
        CloudWatchLogsClient: class {
            async send(c) {
                switch (c.name) {
                    case "PutSubscriptionFilterCommand": state.calls.put.push(c.input.logGroupName); return {};
                    case "ListTagsLogGroupCommand":
                        state.calls.tags.push(c.input.logGroupName);
                        if (state.tagsError) throw state.tagsError;
                        return {tags: state.tags};
                    case "DescribeSubscriptionFiltersCommand":
                        state.calls.describe.push(c.input.logGroupName);
                        return {subscriptionFilters: state.filters};
                    case "DeleteSubscriptionFilterCommand": {
                        const err = state.deleteErrors.shift();
                        if (err) throw err;
                        state.calls.del.push(c.input.logGroupName + ":" + c.input.filterName);
                        return {};
                    }
                    default: return {};
                }
            }
        },
        PutSubscriptionFilterCommand: class PutSubscriptionFilterCommand extends Cmd {},
        DescribeLogGroupsCommand: class DescribeLogGroupsCommand extends Cmd {},
        ListTagsLogGroupCommand: class ListTagsLogGroupCommand extends Cmd {},
        DescribeSubscriptionFiltersCommand: class DescribeSubscriptionFiltersCommand extends Cmd {},
        DeleteSubscriptionFilterCommand: class DeleteSubscriptionFilterCommand extends Cmd {},
    },
    "@aws-sdk/client-lambda": {LambdaClient: class { async send() {} }, InvokeCommand: class extends Cmd {}},
};
const originalLoad = Module._load;
Module._load = function (request, ...rest) { return mocks[request] || originalLoad.call(this, request, ...rest); };
const handler = require(path.join(__dirname, "..", "src", "loggroup-lambda-connector.js")).handler;

function env(pattern = "^$", tags = "nas:logging=external") {
    process.env.DESTINATION_ARN = DEST;
    process.env.LOG_GROUP_PATTERN = pattern;
    process.env.LOG_GROUP_TAGS = tags;
}
const arn = (name) => `arn:aws:logs:us-east-1:111111111111:log-group:${name}`;
const event = (eventName, requestParameters) => ({detail: {eventName, requestParameters}});
const ours = (destinationArn = DEST) => ({filterName: "SumoLGLBDFilter", destinationArn});
const quiet = async (fn) => {  // the handler is chatty; keep test output readable
    const log = console.log, err = console.error;
    console.log = () => {}; console.error = () => {};
    try { return await fn(); } finally { console.log = log; console.error = err; }
};
const run = (e) => quiet(() => handler(e, ctx));
const eventually = async (fn) => { const real = global.setTimeout; global.setTimeout = (f) => real(f, 0); try { return await fn(); } finally { global.setTimeout = real; } };

test("UntagResource removing the matching tag unsubscribes", async () => {
    reset({tags: {}, filters: [ours()]}); env();
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, ["/app/x:SumoLGLBDFilter"]);
});

test("UntagLogGroup (deprecated API) unsubscribes", async () => {
    reset({tags: {}, filters: [ours()]}); env();
    await run(event("UntagLogGroup", {logGroupName: "/app/x", tags: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, ["/app/x:SumoLGLBDFilter"]);
});

test("changing the value so it no longer matches unsubscribes", async () => {
    reset({tags: {"nas:logging": "internal"}, filters: [ours()]}); env();
    await run(event("TagResource", {resourceArn: arn("/app/x"), tags: {"nas:logging": "internal"}}));
    assert.deepStrictEqual(state.calls.del, ["/app/x:SumoLGLBDFilter"]);
    assert.deepStrictEqual(state.calls.put, []);
});

test("another matching tag still keeps and does not remove the subscription", async () => {
    reset({tags: {team: "apps", other: "1"}, filters: [ours()]}); env("^$", "nas:logging=external,team=apps");
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
    assert.deepStrictEqual(state.calls.put, ["/app/x"]);  // still matches, subscribe is idempotent
});

test("a name that still matches LOG_GROUP_PATTERN keeps its subscription", async () => {
    reset({tags: {}, filters: [ours()]}); env("^/aws/lambda");
    await run(event("UntagResource", {resourceArn: arn("/aws/lambda/fn"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
    assert.deepStrictEqual(state.calls.describe, []);
});

test("a filter that points to another destination is never deleted", async () => {
    reset({tags: {}, filters: [ours("arn:aws:lambda:us-east-1:111111111111:function:someone-else")]}); env();
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
});

test("a filter with a different name is never deleted", async () => {
    reset({tags: {}, filters: [{filterName: "SumoLGLBDFilterCustom", destinationArn: DEST}]}); env();
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
});

test("a failed tag lookup keeps the subscription instead of reading as no tags", async () => {
    const denied = Object.assign(new Error("not authorized"), {name: "AccessDeniedException"});
    reset({tagsError: denied, filters: [ours()]}); env();
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
    assert.deepStrictEqual(state.calls.describe, []);
});

test("empty LOG_GROUP_TAGS never unsubscribes", async () => {
    reset({tags: {}, filters: [ours()]}); env("^$", "");
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
    assert.deepStrictEqual(state.calls.tags, []);
});

test("no filter on the log group is a no-op", async () => {
    reset({tags: {}, filters: []}); env();
    await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.deepStrictEqual(state.calls.del, []);
});

test("a log group or filter that is already gone is treated as done", async () => {
    const gone = Object.assign(new Error("The specified log group does not exist."), {name: "ResourceNotFoundException"});
    reset({tags: {}, filters: [ours()], deleteErrors: [gone]}); env();
    const result = await run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]}));
    assert.strictEqual(result.statusCode, 200);
});

test("UntagResource on something that is not a log group is ignored", async () => {
    reset({tags: {}, filters: [ours()]}); env();
    const result = await run(event("UntagResource", {resourceArn: "arn:aws:logs:us-east-1:111111111111:destination:d", tagKeys: ["a"]}));
    assert.strictEqual(result.statusCode, 200);
    assert.deepStrictEqual(state.calls.tags, []);
    assert.deepStrictEqual(state.calls.del, []);
});

test("tagging again subscribes again", async () => {
    reset({tags: {"nas:logging": "external"}, filters: []}); env();
    await run(event("TagResource", {resourceArn: arn("/app/x"), tags: {"nas:logging": "external"}}));
    assert.deepStrictEqual(state.calls.put, ["/app/x"]);
    assert.deepStrictEqual(state.calls.del, []);
});

test("a throttled delete is retried", async () => {
    const throttled = new Error("Rate exceeded");
    reset({tags: {}, filters: [ours()], deleteErrors: [throttled]}); env();
    await eventually(() => run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]})));
    assert.deepStrictEqual(state.calls.del, ["/app/x:SumoLGLBDFilter"]);
});

test("an unexpected delete error is surfaced", async () => {
    const boom = Object.assign(new Error("boom"), {name: "ServiceUnavailableException"});
    reset({tags: {}, filters: [ours()], deleteErrors: [boom]}); env();
    await assert.rejects(run(event("UntagResource", {resourceArn: arn("/app/x"), tagKeys: ["nas:logging"]})), /boom/);
});

test("CreateLogGroup behaviour is unchanged", async () => {
    reset({tags: {}, filters: []}); env("^/aws/lambda");
    await run(event("CreateLogGroup", {logGroupName: "/aws/lambda/new"}));
    await run(event("CreateLogGroup", {logGroupName: "/app/tagged", tags: {"nas:logging": "external"}}));
    await run(event("CreateLogGroup", {logGroupName: "/app/other"}));
    assert.deepStrictEqual(state.calls.put, ["/aws/lambda/new", "/app/tagged"]);
    assert.deepStrictEqual(state.calls.del, []);
});
