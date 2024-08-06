# Guide to Using DTPS Tests

To use the DTPS tests, follow the steps below:

1. **Ensure** that you have a robot running a docker container with the DTPS switchboard.
2. Open a terminal or command prompt.
3. Navigate to the directory where this DTProject is located (i.e. this repository `dt-commons`).
4. Run the following command to execute the tests:

    ```
    dts devel build --pull
    dts devel run -H YOUR_ROBOT_NAME -L test-rpc-call-dtps -- -v /data/ramdisk/dtps:/dtps -e DT_SUPERUSER=1 --privileged
    ```

    This command will initiate the DTPS  RPC call tests.

5. Monitor the test execution in the terminal. You will see the test results and any potential errors or failures.

That's it! You have successfully used the DTPS tests to validate the RPC calls in your robot's docker container running the DTPS switchboard.
